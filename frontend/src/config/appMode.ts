/**
 * True only in the hosted web demo build (built with VITE_APP_MODE=web).
 *
 * The desktop application never sets this, so every web-only element of the
 * interface is absent there and the desktop build is unchanged.
 */
export const IS_WEB = import.meta.env.VITE_APP_MODE === "web";