import { DeliveryReport, EventStatus, PublishParams } from './types';

export interface ClientConfig {
  baseUrl: string;
  apiKey: string;
}

const TERMINAL_STATUSES: ReadonlySet<EventStatus> = new Set([
  'delivered',
  'failed',
]);

export class EventsClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/+$/, '');
    this.apiKey = config.apiKey;
  }

  async publish(params: PublishParams): Promise<DeliveryReport> {
    const res = await fetch(`${this.baseUrl}/publish`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': this.apiKey,
        ...(params.headers ?? {}),
      },
      body: JSON.stringify({
        topic: params.topic,
        payload: params.payload,
        partitionKey: params.partitionKey ?? params.topic,
      }),
    });
    if (!res.ok) {
      throw new Error(`publish to ${params.topic} failed: ${res.status}`);
    }
    return (await res.json()) as DeliveryReport;
  }

  isTerminal(report: DeliveryReport): boolean {
    return TERMINAL_STATUSES.has(report.status);
  }
}
