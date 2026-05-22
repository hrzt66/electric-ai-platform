package service

import "testing"

func TestFormatSSE_MultilinePayloadSplitsIntoMultipleDataLines(t *testing.T) {
	got := FormatSSE("snapshot", []byte("line1\nline2\nline3"))
	want := "event: snapshot\n" +
		"data: line1\n" +
		"data: line2\n" +
		"data: line3\n\n"
	if got != want {
		t.Fatalf("unexpected sse format:\nwant=%q\ngot =%q", want, got)
	}
}

