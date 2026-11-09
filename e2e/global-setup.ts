import { mkdirSync } from "node:fs";

import { expect, request } from "@playwright/test";

import { ADA, ADA_STATE, ADMIN, Api, BASE_URL, BO, BOOTSTRAP_PASSWORD } from "./support";

/**
 * A fresh stack has only the bootstrap admin. This sets the admin's own password, adds two
 * editors who are writers, a field and a unit, and keeps Ada's session for the tests.
 * Everything is synthetic.
 */
async function changePassword(email: string, current: string, next: string): Promise<void> {
  const http = await request.newContext({ baseURL: BASE_URL });
  const login = await http.post("/api/v1/auth/login", { data: { email, password: current } });
  expect(login.status(), await login.text()).toBe(200);
  const { access_token: token } = (await login.json()) as { access_token: string };
  const changed = await http.post("/api/v1/auth/change-password", {
    headers: { Authorization: `Bearer ${token}` },
    data: { current_password: current, new_password: next },
  });
  expect(changed.status(), await changed.text()).toBe(200);
  await http.dispose();
}

async function alreadySetUp(): Promise<boolean> {
  const http = await request.newContext({ baseURL: BASE_URL });
  const login = await http.post("/api/v1/auth/login", { data: ADMIN });
  await http.dispose();
  return login.status() === 200;
}

export default async function globalSetup(): Promise<void> {
  // A stack kept from an earlier run (E2E_KEEP=1) has its people already.
  if (!(await alreadySetUp())) await setUp();
  await keepSession();
}

async function setUp(): Promise<void> {
  await changePassword(ADMIN.email, BOOTSTRAP_PASSWORD, ADMIN.password);
  const admin = await Api.signIn(ADMIN);

  const field = await admin.send<{ id: string }>("post", "/lists/fields", { values: { name_en: "STEM" } }, 201);
  await admin.send(
    "post",
    "/lists/units",
    { values: { name_en: "School of Examples", default_field_id: field.id } },
    201,
  );

  for (const person of [ADA, BO]) {
    const created = await admin.send<{ user: { id: string }; initial_password: string | null }>(
      "post",
      "/users",
      { email: person.email, full_name: person.name, role: "editor", language: "en" },
      201,
    );
    // The stack sends no email, so the temporary password comes back.
    expect(created.initial_password).toBeTruthy();
    await changePassword(person.email, created.initial_password as string, person.password);
    await admin.send(
      "post",
      "/lists/writers",
      { values: { display_name_en: person.name.split(" ")[0], user_id: created.user.id } },
      201,
    );
  }
  await admin.dispose();
}

async function keepSession(): Promise<void> {
  // Ada's session cookie, so most tests start signed in, as after a working day's first visit.
  mkdirSync(".auth", { recursive: true });
  const http = await request.newContext({ baseURL: BASE_URL });
  const login = await http.post("/api/v1/auth/login", { data: { email: ADA.email, password: ADA.password } });
  expect(login.status()).toBe(200);
  await http.storageState({ path: ADA_STATE });
  await http.dispose();
}
