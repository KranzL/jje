package index

import "testing"

func TestResolveBatches(t *testing.T) {
	ix := Build([]string{"a", "b", "c", "d", "e", "f"})
	batches := make([][]string, 16)
	for i := range batches {
		batches[i] = []string{"a", "c", "e", "z"}
	}
	got := ix.ResolveBatches(batches)
	if len(got) != len(batches) {
		t.Fatalf("want %d results, got %d", len(batches), len(got))
	}
	for i, v := range got {
		if v != got[0] {
			t.Fatalf("slot %d diverged: %d vs %d", i, v, got[0])
		}
	}
}
