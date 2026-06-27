# @acme/events-client

A small typed client for the Events delivery service.

## Install

```sh
npm install @acme/events-client
```

## Usage

```ts
import { EventsClient } from '@acme/events-client';

const client = new EventsClient({
  baseUrl: 'https://api.example.com',
  apiKey: process.env.EVENTS_KEY ?? '',
});

const report = await client.publish({ topic: 'orders', payload: { id: 7 } });
if (client.isTerminal(report)) {
  console.log(report.status, report.attempts);
}
```

## Delivery status

`publish` resolves with a `DeliveryReport`. The `status` field reports the
outcome the broker recorded for the event:

- `queued` - accepted and awaiting a delivery attempt
- `delivered` - acknowledged by the destination
- `failed` - exhausted all delivery attempts

The broker only ever reports one of these values back to the client.

## Versioning

This package follows semver. The `3.2.x` line is a feature release over `3.1.x`
and remains backward compatible with all `3.x` consumers.
