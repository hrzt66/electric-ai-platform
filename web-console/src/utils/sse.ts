export type SseMessage = {
  event: string
  data: string
  id?: string
}

export type StreamSseOptions = {
  headers?: Record<string, string>
  signal?: AbortSignal
  onOpen?: () => void
  onError?: (error: unknown) => void
  onMessage?: (message: SseMessage) => void
}

function parseChunk(buffer: string) {
  const messages: SseMessage[] = []
  const normalizedBuffer = buffer.replace(/\r\n/g, '\n')
  const parts = normalizedBuffer.split('\n\n')
  const remainder = parts.pop() ?? ''

  for (const part of parts) {
    const lines = part.split('\n')
    let event = 'message'
    let data = ''
    let id: string | undefined

    for (const rawLine of lines) {
      const line = rawLine.trimEnd()
      if (!line || line.startsWith(':')) {
        continue
      }
      const idx = line.indexOf(':')
      const field = idx === -1 ? line : line.slice(0, idx)
      const value = idx === -1 ? '' : line.slice(idx + 1).trimStart()

      if (field === 'event') {
        event = value || 'message'
      } else if (field === 'data') {
        data = data ? `${data}\n${value}` : value
      } else if (field === 'id') {
        id = value
      }
    }

    messages.push({ event, data, id })
  }

  return { messages, remainder }
}

export async function streamSse(url: string, options: StreamSseOptions = {}) {
  const controller = new AbortController()
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort()
    } else {
      options.signal.addEventListener('abort', () => controller.abort(), { once: true })
    }
  }

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'text/event-stream',
        ...options.headers,
      },
      cache: 'no-store',
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`SSE request failed: ${response.status}`)
    }

    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('text/event-stream')) {
      throw new Error(`Unexpected content-type for SSE: ${contentType}`)
    }

    options.onOpen?.()

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('SSE response has no readable body')
    }

    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const parsed = parseChunk(buffer)
      buffer = parsed.remainder
      for (const message of parsed.messages) {
        options.onMessage?.(message)
      }
    }

    try {
      reader.releaseLock()
    } catch {
      // ignore
    }
  } catch (error) {
    if (!controller.signal.aborted) {
      options.onError?.(error)
    }
    throw error
  }
}
