import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { http } from "../../api/client";
import { errorMessage } from "../../api/errors";
import type { CustomField, PasswordReset, User, UserCreated, UserRole } from "../../api/types";
import { useAuth } from "../../auth";
import { useBrand } from "../../brand";
import ConfirmButton from "../../components/ConfirmButton";
import { SelectField, TextField } from "../../components/fields/Autosave";
import { useToast } from "../../components/Toast";
import { formatDate } from "../../dates";
import { SectionHeader, SubHeading } from "./SettingsLayout";

const ROLES: UserRole[] = ["admin", "editor", "viewer"];
const USERS_KEY = ["users"];
const FIELDS_KEY = ["custom-fields"];

function useRoleOptions() {
  const { t } = useTranslation();
  return ROLES.map((role) => ({ value: role, label: t(`user_menu.roles.${role}`) }));
}

/** Shown only when an email could not be sent, so the admin can pass the password on. */
function TemporaryPassword({ email, password }: { email: string; password: string }) {
  const { t } = useTranslation();
  return (
    <p role="status" className="notice-info mt-4xs max-w-3xl">
      {t("settings.users.no_email", { email })} <code className="font-semibold">{password}</code>
    </p>
  );
}

function InviteForm({ onPassword }: { onPassword: (email: string, password: string) => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const roles = useRoleOptions();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("editor");
  const [language, setLanguage] = useState("");
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    try {
      const result = await http.post<UserCreated>("/users", {
        email,
        full_name: fullName || null,
        role,
        language: language || null,
      });
      if (result.initial_password) {
        onPassword(result.user.email, result.initial_password);
      } else {
        toast({ text: t("settings.users.invited", { email: result.user.email }) });
      }
      setEmail("");
      setFullName("");
      await queryClient.invalidateQueries({ queryKey: USERS_KEY });
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="max-w-3xl">
      <div className="grid gap-4xs sm:grid-cols-4">
        <div>
          <label className="field-label" htmlFor="invite-email">
            {t("settings.users.email")}
          </label>
          <input
            id="invite-email"
            className="input"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="invite-name">
            {t("settings.users.name")}
          </label>
          <input
            id="invite-name"
            className="input"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="invite-role">
            {t("settings.users.role")}
          </label>
          <select
            id="invite-role"
            className="input"
            value={role}
            onChange={(event) => setRole(event.target.value as UserRole)}
          >
            {roles.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="invite-language">
            {t("settings.users.email_language")}
          </label>
          <select
            id="invite-language"
            className="input"
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            <option value="">{t("settings.users.language_english_default")}</option>
            <option value="ja">{t("settings.users.language_japanese")}</option>
          </select>
        </div>
      </div>
      {error !== null && (
        <p role="alert" className="field-error">
          {errorMessage(t, error)}
        </p>
      )}
      <button type="submit" className="btn-primary mt-4xs">
        {t("settings.users.invite")}
      </button>
    </form>
  );
}

function UserRow({
  user,
  isSelf,
  onPassword,
}: {
  user: User;
  isSelf: boolean;
  onPassword: (email: string, password: string) => void;
}) {
  const { t } = useTranslation();
  const { timezone } = useBrand();
  const queryClient = useQueryClient();
  const toast = useToast();
  const roles = useRoleOptions();
  const [error, setError] = useState<unknown>(null);

  async function update(changes: Partial<User>): Promise<void> {
    await http.patch(`/users/${user.id}`, changes);
    await queryClient.invalidateQueries({ queryKey: USERS_KEY });
  }

  async function setActive(active: boolean): Promise<void> {
    setError(null);
    try {
      await update({ is_active: active });
      if (!active) {
        toast({
          text: t("settings.users.switched_off", { email: user.email }),
          undo: () => void setActive(true),
        });
      }
    } catch (failure) {
      setError(failure);
    }
  }

  async function resetPassword(): Promise<void> {
    setError(null);
    try {
      const result = await http.post<PasswordReset>(`/users/${user.id}/reset-password`);
      if (result.initial_password) {
        onPassword(user.email, result.initial_password);
      } else {
        toast({ text: t("settings.users.reset_sent", { email: user.email }) });
      }
    } catch (failure) {
      setError(failure);
    }
  }

  return (
    <tr className={user.is_active ? undefined : "opacity-60"}>
      <td>
        <TextField
          label={t("settings.users.name")}
          value={user.full_name}
          save={(value) => update({ full_name: value })}
        />
      </td>
      <td>
        <TextField
          label={t("settings.users.email")}
          type="email"
          value={user.email}
          save={(value) => update({ email: value })}
        />
      </td>
      <td>
        <SelectField
          label={t("settings.users.role")}
          value={user.role}
          save={(value) => update({ role: value as UserRole })}
          options={roles}
          disabled={isSelf}
        />
      </td>
      <td className="text-center">
        <input
          type="checkbox"
          aria-label={t("common.active")}
          checked={user.is_active}
          disabled={isSelf}
          onChange={(event) => void setActive(event.target.checked)}
        />
      </td>
      <td className="whitespace-nowrap text-content-secondary">
        {user.last_login_at
          ? formatDate(user.last_login_at, timezone)
          : t("settings.users.never")}
      </td>
      <td>
        {!isSelf && (
          <ConfirmButton
            label={t("settings.users.new_password")}
            question={t("settings.users.new_password_question")}
            onConfirm={() => void resetPassword()}
          />
        )}
        {error !== null && (
          <p role="alert" className="field-error">
            {errorMessage(t, error)}
          </p>
        )}
      </td>
    </tr>
  );
}

function PersonalFields({ users }: { users: User[] }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: FIELDS_KEY,
    queryFn: () => http.get<CustomField[]>("/custom-fields"),
  });
  const fields = (data ?? []).filter((field) => field.scope === "personal");
  const owners = users
    .filter((user) => user.is_active && user.role !== "viewer")
    .map((user) => ({ value: user.id, label: user.full_name ?? user.email }));
  const refresh = () => queryClient.invalidateQueries({ queryKey: FIELDS_KEY });

  if (fields.length === 0) return null;
  return (
    <>
      <SubHeading>{t("settings.users.personal_title")}</SubHeading>
      <p className="mb-4xs max-w-3xl text-content-secondary">{t("settings.users.personal_help")}</p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.users.personal_field")}</th>
              <th>{t("settings.users.personal_owner")}</th>
              <th>{t("settings.users.personal_transfer")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.id}>
                <td>{field.label_en}</td>
                <td>
                  {field.owner_name}
                  {field.owner_active === false && (
                    <span className="chip ml-5xs">{t("settings.users.former_user")}</span>
                  )}
                </td>
                <td>
                  <SelectField
                    label={t("settings.users.personal_transfer")}
                    value={field.owner_id}
                    save={async (value) => {
                      const result = await http.post(`/custom-fields/${field.id}/transfer`, {
                        owner_id: value,
                      });
                      await refresh();
                      return result;
                    }}
                    options={
                      owners.some((owner) => owner.value === field.owner_id)
                        ? owners
                        : [
                            { value: field.owner_id ?? "", label: field.owner_name ?? "" },
                            ...owners,
                          ]
                    }
                  />
                </td>
                <td>
                  <ConfirmButton
                    label={t("settings.users.personal_convert")}
                    question={t("settings.users.personal_convert_question")}
                    onConfirm={() =>
                      void http.post(`/custom-fields/${field.id}/convert`).then(refresh)
                    }
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function UsersSettings() {
  const { t } = useTranslation();
  const { user: me } = useAuth();
  const { data } = useQuery({
    queryKey: USERS_KEY,
    queryFn: () => http.get<User[]>("/users"),
    refetchInterval: 60_000,
  });
  const [temporary, setTemporary] = useState<{ email: string; password: string } | null>(null);
  const showPassword = (email: string, password: string) => setTemporary({ email, password });

  return (
    <div>
      <SectionHeader title={t("settings.sections.users")} help={t("settings.help.users")} />
      <InviteForm onPassword={showPassword} />
      {temporary && <TemporaryPassword email={temporary.email} password={temporary.password} />}

      <SubHeading>{t("settings.users.people")}</SubHeading>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t("settings.users.name")}</th>
              <th>{t("settings.users.email")}</th>
              <th>{t("settings.users.role")}</th>
              <th>{t("common.active")}</th>
              <th>{t("settings.users.last_sign_in")}</th>
              <th>{t("common.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((user) => (
              <UserRow
                key={user.id}
                user={user}
                isSelf={user.id === me?.id}
                onPassword={showPassword}
              />
            ))}
          </tbody>
        </table>
      </div>
      <PersonalFields users={data ?? []} />
    </div>
  );
}
