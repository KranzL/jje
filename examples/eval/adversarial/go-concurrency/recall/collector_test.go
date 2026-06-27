package collector

import (
	"strconv"
	"sync"
	"testing"
	"time"
)

func TestCollectorWatch(t *testing.T) {
	c := New()
	stop := make(chan struct{})
	out := make(chan Sample, 64)

	go c.Watch(time.Millisecond, out, stop)
	go func() {
		for range out {
		}
	}()

	var wg sync.WaitGroup
	for w := 0; w < 8; w++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			for i := 0; i < 2000; i++ {
				c.Record("k" + strconv.Itoa((id+i)%37))
			}
		}(w)
	}
	wg.Wait()

	close(stop)
	c.Close()

	if got := c.TopN(3); len(got) == 0 {
		t.Fatal("expected labels")
	}
}
