package httpx

type Response[T any] struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    T      `json:"data"`
	TraceID string `json:"trace_id"`
}

func OK[T any](data T, traceID string) Response[T] {
	return Response[T]{Code: 0, Message: "success", Data: data, TraceID: traceID}
}
