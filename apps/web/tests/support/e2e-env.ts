export const E2E_API_PORT = 8100

export function resolveE2EWebPort(
  raw = process.env.GAVIN_E2E_WEB_PORT || '3100',
): number {
  const port = Number(raw)
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error('GAVIN_E2E_WEB_PORT must be an integer between 1 and 65535')
  }
  if (port === E2E_API_PORT) {
    throw new Error(`GAVIN_E2E_WEB_PORT must differ from the API port ${E2E_API_PORT}`)
  }
  return port
}
