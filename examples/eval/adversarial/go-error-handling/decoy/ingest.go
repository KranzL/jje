package ingest

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
)

var ErrRejected = errors.New("record rejected by policy")

type sink interface {
	Write(ctx context.Context, payload []byte) error
	Close(ctx context.Context) error
}

type validator interface {
	Check(payload []byte) error
}

type Pipeline struct {
	out sink
	val validator
	log *slog.Logger
}

func NewPipeline(out sink, val validator, log *slog.Logger) *Pipeline {
	return &Pipeline{out: out, val: val, log: log}
}

func (p *Pipeline) Handle(ctx context.Context, payload []byte) error {
	if err := p.val.Check(payload); err != nil {
		return fmt.Errorf("validate: %w", err)
	}
	if err := p.out.Write(ctx, payload); err != nil {
		return fmt.Errorf("write %d bytes: %w", len(payload), err)
	}
	return nil
}

func (p *Pipeline) Drain(ctx context.Context, batch [][]byte) error {
	var rejected int
	for _, payload := range batch {
		err := p.Handle(ctx, payload)
		if err == nil {
			continue
		}
		if errors.Is(err, ErrRejected) {
			rejected++
			p.log.WarnContext(ctx, "dropping record", "reason", fmt.Sprintf("%v", err))
			continue
		}
		return err
	}
	if rejected > 0 {
		return fmt.Errorf("%d of %d records rejected: %w", rejected, len(batch), ErrRejected)
	}
	return nil
}

func (p *Pipeline) Shutdown(ctx context.Context) error {
	if err := p.out.Close(ctx); err != nil {
		p.log.ErrorContext(ctx, "sink close failed", "err", err)
		return fmt.Errorf("close sink: %w", err)
	}
	return nil
}
