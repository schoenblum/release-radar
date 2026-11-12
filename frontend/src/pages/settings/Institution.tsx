import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { Institution, LandingView, UserRole } from "../../api/types";
import { SelectField, TextField } from "../../components/fields/Autosave";
import { useFieldSaver } from "../../components/fields/useFieldSaver";
import { MAX_SHOWN, offsetLabel, standardOffset, zoneChoices, zoneName } from "../../timeZones";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const ROLES: UserRole[] = ["admin", "editor", "viewer"];
const QUERY_KEY = ["settings", "institution"];

function monthNames(language: string): { value: string; label: string }[] {
  const format = new Intl.DateTimeFormat(language, { month: "long" });
  return Array.from({ length: 12 }, (_, month) => ({
    value: String(month + 1),
    label: format.format(new Date(2026, month, 1)),
  }));
}

/**
 * Up to three further zones a release time shows in, besides the institution's own: a choice
 * per place, in the order they show; each place can stay empty (Daniel, 2026-11-12). The
 * choices are a list of time zones, west to east by their standard offset (Daniel, 2026-11-13);
 * daylight saving is applied on each date by itself.
 */
export function DisplayZones({
  institution,
  save,
}: {
  institution: Institution;
  save: (value: unknown, version: number) => Promise<unknown>;
}) {
  const { t, i18n } = useTranslation();
  const [error, setError] = useState<unknown>(null);
  const places = Array.from(
    { length: MAX_SHOWN },
    (_, place) => institution.display_time_zones[place] ?? null,
  );
  const offered = zoneChoices(institution.timezone).map((zone) => ({
    key: zone.key,
    label: `${offsetLabel(standardOffset(zone.key))} ${zoneName(zone.key, i18n.language)}`,
  }));
  const listed = new Set(offered.map((option) => option.key));

  function choose(place: number, value: string | null): void {
    setError(null);
    // A zone chosen again moves here from its old place.
    const next = places.map((zone, index) =>
      index === place ? value : zone === value ? null : zone,
    );
    save(next, institution.field_versions.display_time_zones ?? 0).catch((failure: unknown) =>
      setError(failure),
    );
  }

  return (
    <fieldset className="sm:col-span-2">
      <legend className="field-label">{t("settings.institution.display_zones")}</legend>
      <p className="field-hint mb-4xs mt-0">
        {t("settings.institution.display_zones_hint", { count: MAX_SHOWN })}
      </p>
      <div className="grid gap-4xs sm:grid-cols-3">
        {places.map((zone, place) => (
          <label key={place} className="block">
            <span className="text-sm text-content-secondary">
              {t("settings.institution.display_zone_place", { place: place + 1 })}
            </span>
            <select
              className="input"
              value={zone ?? ""}
              onChange={(event) => choose(place, event.target.value || null)}
            >
              <option value="">{t("settings.institution.display_zone_none")}</option>
              {zone && !listed.has(zone) && (
                <option value={zone}>{zoneName(zone, i18n.language)}</option>
              )}
              {offered.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
    </fieldset>
  );
}

export default function InstitutionSettings() {
  const { t, i18n } = useTranslation();
  const { data } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => http.get<Institution>("/settings/institution"),
  });
  // The header, footer and every date read the name and timezone from the brand.
  const saver = useFieldSaver("/settings/institution", QUERY_KEY, ["brand"]);
  if (!data) return null;

  const versions = data.field_versions;
  const zones = Intl.supportedValuesOf("timeZone");
  const timezones = (zones.includes(data.timezone) ? zones : [data.timezone, ...zones]).map(
    (zone) => ({ value: zone, label: zone }),
  );

  function saveLanding(role: UserRole) {
    return (value: string, version: number) =>
      saver("landing_pages")({ ...data!.landing_pages, [role]: value as LandingView }, version);
  }

  return (
    <div>
      <SectionHeader title={t("settings.sections.institution")} help={t("settings.help.institution")} />
      <div className="grid max-w-3xl gap-2xs sm:grid-cols-2">
        <div>
          <label className="field-label" htmlFor="name-en">
            {t("settings.institution.name_en")}
          </label>
          <TextField
            id="name-en"
            className="input"
            label={t("settings.institution.name_en")}
            value={data.name_en}
            version={versions.name_en}
            save={saver("name_en")}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="name-ja">
            {t("settings.institution.name_ja")}
          </label>
          <TextField
            id="name-ja"
            className="input"
            label={t("settings.institution.name_ja")}
            value={data.name_ja}
            version={versions.name_ja}
            save={saver("name_ja")}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="timezone">
            {t("settings.institution.timezone")}
          </label>
          <SelectField
            id="timezone"
            className="input"
            label={t("settings.institution.timezone")}
            value={data.timezone}
            version={versions.timezone}
            save={saver("timezone")}
            options={timezones}
            hint={t("settings.institution.timezone_hint")}
          />
        </div>
        <DisplayZones institution={data} save={saver("display_time_zones")} />
        <div>
          <label className="field-label" htmlFor="ay-start">
            {t("settings.institution.ay_start")}
          </label>
          <SelectField
            id="ay-start"
            className="input"
            label={t("settings.institution.ay_start")}
            value={String(data.ay_start_month)}
            version={versions.ay_start_month}
            save={(value, version) => saver("ay_start_month")(Number(value), version)}
            options={monthNames(i18n.language)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="website-domain">
            {t("settings.institution.website_domain")}
          </label>
          <TextField
            id="website-domain"
            className="input"
            label={t("settings.institution.website_domain")}
            value={data.website_domain}
            version={versions.website_domain}
            save={saver("website_domain")}
            hint={t("settings.institution.website_domain_hint")}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="contact-email">
            {t("settings.institution.contact_email")}
          </label>
          <TextField
            id="contact-email"
            className="input"
            type="email"
            label={t("settings.institution.contact_email")}
            value={data.contact_email}
            version={versions.contact_email}
            save={saver("contact_email")}
            hint={t("settings.institution.contact_email_hint")}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="code-pattern">
            {t("settings.institution.code_pattern")}
          </label>
          <TextField
            id="code-pattern"
            className="input"
            label={t("settings.institution.code_pattern")}
            value={data.release_code_pattern}
            version={versions.release_code_pattern}
            save={saver("release_code_pattern")}
            hint={t("settings.institution.code_pattern_hint")}
          />
        </div>
      </div>

      <SubHeading>{t("settings.institution.landing")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">
        {t("settings.institution.landing_hint")}
      </p>
      <div className="grid max-w-3xl gap-2xs sm:grid-cols-3">
        {ROLES.map((role) => (
          <div key={role}>
            <label className="field-label" htmlFor={`landing-${role}`}>
              {t(`user_menu.roles.${role}`)}
            </label>
            <SelectField
              id={`landing-${role}`}
              className="input"
              label={t(`user_menu.roles.${role}`)}
              value={data.landing_pages[role]}
              version={versions.landing_pages}
              save={saveLanding(role)}
              options={[
                { value: "mine", label: t("settings.institution.landing_mine") },
                { value: "all", label: t("settings.institution.landing_all") },
                { value: "analysis", label: t("settings.institution.landing_analysis") },
              ]}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
