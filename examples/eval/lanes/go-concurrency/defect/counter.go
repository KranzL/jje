package counter

import "sync"

type Counter struct {
	value int
}

func (c *Counter) Add(delta int) {
	c.value += delta
}

func (c *Counter) Value() int {
	return c.value
}

func SumConcurrently(n, perGoroutine int) int {
	c := &Counter{}
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < perGoroutine; j++ {
				c.Add(1)
			}
		}()
	}
	wg.Wait()
	return c.Value()
}
