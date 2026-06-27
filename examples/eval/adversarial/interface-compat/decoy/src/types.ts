export type EventStatus = 'queued' | 'delivered' | 'failed';

export interface PublishParams {
  topic: string;
  payload: unknown;
  partitionKey?: string;
  headers?: Record<string, string>;
}

export interface DeliveryReport {
  eventId: string;
  status: EventStatus;
  attempts: number;
  acceptedAt: string;
}
