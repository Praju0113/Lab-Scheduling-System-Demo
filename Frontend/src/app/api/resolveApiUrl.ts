const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

export function resolveApiBaseUrl() {
  // @ts-ignore
  const configuredApiUrl = import.meta.env.VITE_API_URL;
  // @ts-ignore
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  const rawUrl = configuredApiUrl || configuredApiBaseUrl;

  if (!rawUrl) {
    return '/api';
  }

  const normalizedUrl = trimTrailingSlash(rawUrl);
  return /\/api$/i.test(normalizedUrl) ? normalizedUrl : `${normalizedUrl}/api`;
}

export function resolveApiOrigin() {
  const apiBaseUrl = resolveApiBaseUrl();
  return apiBaseUrl.replace(/\/api$/i, '');
}
