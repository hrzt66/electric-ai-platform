package service

import "bytes"

// FormatSSE returns a minimal standards-compatible Server-Sent Events message.
//
// Format:
//   event: <eventName>\n
//   data: <payload-line-1>\n
//   data: <payload-line-2>\n
//   \n
//
// We intentionally keep it minimal for Task 4 scope; no id/retry/extra fields.
func FormatSSE(eventName string, payload []byte) string {
	if eventName == "" {
		eventName = "message"
	}

	// Per SSE rules, each line of data must be prefixed with "data:".
	lines := bytes.Split(payload, []byte("\n"))
	out := "event: " + eventName + "\n"
	for _, line := range lines {
		out += "data: " + string(line) + "\n"
	}
	out += "\n"
	return out
}
