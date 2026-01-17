/* eslint-disable react-hooks/exhaustive-deps */
'use client'

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, CheckCircle, Info } from 'lucide-react'
import { notificationEventName, NotificationPayload } from '@/lib/notifications'

const AUTO_CLOSE_MS = 5000

export default function GlobalAlert() {
  const [notification, setNotification] = useState<NotificationPayload | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<NotificationPayload>
      setNotification(customEvent.detail)
    }

    window.addEventListener(notificationEventName, handler as EventListener)
    return () => window.removeEventListener(notificationEventName, handler as EventListener)
  }, [])

  useEffect(() => {
    if (!notification) return
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }
    timerRef.current = setTimeout(() => setNotification(null), AUTO_CLOSE_MS)
  }, [notification])

  if (!notification) return null

  const iconMap = {
    error: <AlertCircle className="h-5 w-5 text-red-600" />,
    info: <Info className="h-5 w-5 text-blue-600" />,
    success: <CheckCircle className="h-5 w-5 text-green-600" />,
  }

  const bgMap = {
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    success: 'bg-green-50 border-green-200 text-green-800',
  }

  return (
    <div className="fixed top-4 right-4 z-[100] max-w-sm w-full">
      <div className={`flex items-start space-x-3 rounded-lg border p-4 shadow-lg ${bgMap[notification.type]}`}>
        {iconMap[notification.type]}
        <div className="flex-1 text-sm font-medium leading-5">{notification.message}</div>
        <button
          onClick={() => setNotification(null)}
          aria-label="Dismiss"
          className="text-xs font-semibold opacity-70 hover:opacity-100"
        >
          Close
        </button>
      </div>
    </div>
  )
}
