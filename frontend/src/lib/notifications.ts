const NOTIFICATION_EVENT = 'app-notification'

export type NotificationPayload = {
  type: 'error' | 'info' | 'success'
  message: string
}

export const notificationEventName = NOTIFICATION_EVENT

export function notify(payload: NotificationPayload) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(NOTIFICATION_EVENT, { detail: payload }))
}

export function notifyError(message: string) {
  notify({ type: 'error', message })
}

export function notifyInfo(message: string) {
  notify({ type: 'info', message })
}

export function notifySuccess(message: string) {
  notify({ type: 'success', message })
}
