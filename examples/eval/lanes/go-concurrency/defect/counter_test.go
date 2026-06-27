package counter

import "testing"

func TestSumConcurrently(t *testing.T) {
	got := SumConcurrently(8, 1000)
	if got != 8000 {
		t.Fatalf("SumConcurrently = %d, want 8000", got)
	}
}
