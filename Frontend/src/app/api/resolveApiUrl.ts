const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '');

const getRequiredApiUrl = () => {
  // @ts-ignore
  const configuredApiUrl = import.meta.env.VITE_API_URL;
  // @ts-ignore
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  const rawUrl = configuredApiUrl || configuredApiBaseUrl;

  if (rawUrl) {
    return rawUrl;
  }

  throw new Error('Missing required environment variable: VITE_API_BASE_URL or VITE_API_URL');
};

export function resolveApiBaseUrl() {
  const normalizedUrl = trimTrailingSlash(getRequiredApiUrl());
  return /\/api$/i.test(normalizedUrl) ? normalizedUrl : `${normalizedUrl}/api`;
}

export function resolveApiOrigin() {
  const apiBaseUrl = resolveApiBaseUrl();
  return apiBaseUrl.replace(/\/api$/i, '');
}
