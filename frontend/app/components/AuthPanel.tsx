"use client";

import { useState, type FormEvent } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type AuthUser = {
  id: number;
  email: string;
  is_active: boolean;
};

type AuthPanelProps = {
  onAuthenticated?: (token: string, user: AuthUser) => void;
};

export default function AuthPanel({
  onAuthenticated,
}: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function readError(response: Response): Promise<string> {
    const body = await response.json().catch(() => null);

    if (Array.isArray(body?.detail)) {
      return body.detail
        .map((item: { msg?: string }) => item.msg ?? "Invalid input")
        .join(". ");
    }

    return body?.detail ?? "Something went wrong. Please try again.";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);

    try {
      if (mode === "register") {
        const registration = await fetch(
          `${API_BASE_URL}/api/auth/register`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          },
        );

        if (!registration.ok) {
          throw new Error(await readError(registration));
        }
      }

      const login = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!login.ok) {
        throw new Error(await readError(login));
      }

      const tokenData: { access_token: string; token_type: string } =
        await login.json();

      const profileResponse = await fetch(
        `${API_BASE_URL}/api/auth/me`,
        {
          headers: {
            Authorization: `Bearer ${tokenData.access_token}`,
          },
        },
      );

      if (!profileResponse.ok) {
        throw new Error(await readError(profileResponse));
      }

      const user: AuthUser = await profileResponse.json();

      // Keep the short-lived token for this browser tab/session only.
      sessionStorage.setItem("jobshield_access_token", tokenData.access_token);

      setPassword("");
      setSuccess(
        mode === "register"
          ? "Account created and login successful!"
          : "Login successful!",
      );

      onAuthenticated?.(tokenData.access_token, user);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot connect to JobShield API. Make sure the backend is running."
          : err instanceof Error
            ? err.message
            : "Something went wrong. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 text-gray-900 shadow-sm">
      <h2 className="text-2xl font-bold">
        {mode === "login" ? "Welcome back" : "Create your account"}
      </h2>
      <p className="mt-2 text-sm text-gray-600">
        {mode === "login"
          ? "Sign in to continue with JobShield."
          : "Register to start using JobShield."}
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label htmlFor="auth-email" className="mb-1 block text-sm font-medium">
            Email address
          </label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label
            htmlFor="auth-password"
            className="mb-1 block text-sm font-medium"
          >
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
            minLength={mode === "register" ? 12 : 1}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
            placeholder={
              mode === "register"
                ? "At least 12 characters"
                : "Enter your password"
            }
          />
        </div>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        {success && (
          <p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
            {success}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-blue-700 px-4 py-3 font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading
            ? "Please wait..."
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-gray-600">
        {mode === "login" ? "New to JobShield?" : "Already have an account?"}{" "}
        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError("");
            setSuccess("");
          }}
          className="font-semibold text-blue-700 hover:underline"
        >
          {mode === "login" ? "Create an account" : "Sign in"}
        </button>
      </p>
    </section>
  );
}
