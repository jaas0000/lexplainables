export class BeheerFetchFout extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

export async function beheerFetch(pad: string, init: RequestInit = {}) {
  const res = await fetch(pad, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (res.status === 401) {
    window.location.href = "/login";
    throw new BeheerFetchFout(401, "Niet geautoriseerd.");
  }
  if (!res.ok) {
    const detail = await res
      .json()
      .then((d: { detail?: string }) => d.detail)
      .catch(() => null);
    throw new BeheerFetchFout(
      res.status,
      detail ?? `${res.status} ${res.statusText}`,
    );
  }
  if (res.status === 204) return undefined;
  return res.json();
}
