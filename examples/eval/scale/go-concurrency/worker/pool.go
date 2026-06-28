package worker

import (
	"context"
	"sync"

	"github.com/acme/telemetry/metrics"
)

type Job struct {
	Key     string
	Payload []byte
}

type Handler func(ctx context.Context, j Job) error

type Pool struct {
	size    int
	handler Handler
	reg     *metrics.Registry
}

func NewPool(size int, h Handler, reg *metrics.Registry) *Pool {
	if size < 1 {
		size = 1
	}
	return &Pool{size: size, handler: h, reg: reg}
}

func (p *Pool) Run(ctx context.Context, jobs <-chan Job) {
	var wg sync.WaitGroup
	for i := 0; i < p.size; i++ {
		wg.Add(1)
		go func(worker int) {
			defer wg.Done()
			p.consume(ctx, worker, jobs)
		}(i)
	}
	wg.Wait()
}

func (p *Pool) consume(ctx context.Context, worker int, jobs <-chan Job) {
	for {
		select {
		case <-ctx.Done():
			return
		case j, ok := <-jobs:
			if !ok {
				return
			}
			if err := p.handler(ctx, j); err != nil {
				p.reg.Add("jobs.failed", 1)
				continue
			}
			p.reg.Add("jobs.ok", 1)
		}
	}
}

func FanOut(ctx context.Context, jobs []Job, workers int, h Handler) []error {
	in := make(chan Job)
	errs := make([]error, len(jobs))
	idx := make(chan int)

	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				i, ok := <-idx
				if !ok {
					return
				}
				errs[i] = h(ctx, jobs[i])
			}
		}()
	}

	go func() {
		for i := range jobs {
			select {
			case <-ctx.Done():
			case idx <- i:
			}
		}
		close(idx)
		close(in)
	}()

	wg.Wait()
	return errs
}
