package index

import "sync"

type Index struct {
	offsets map[string]int
}

func Build(terms []string) *Index {
	offsets := make(map[string]int, len(terms))
	for i, t := range terms {
		if _, seen := offsets[t]; !seen {
			offsets[t] = i
		}
	}
	return &Index{offsets: offsets}
}

func (ix *Index) ResolveBatches(batches [][]string) []int {
	out := make([]int, len(batches))
	var wg sync.WaitGroup
	for i, batch := range batches {
		wg.Add(1)
		go func(slot int, items []string) {
			defer wg.Done()
			acc := 0
			for _, it := range items {
				if off, ok := ix.offsets[it]; ok {
					acc += off
				}
			}
			out[slot] = acc
		}(i, batch)
	}
	wg.Wait()
	return out
}
