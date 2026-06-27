# @acme/docs-client

A small typed client for the Documents service.

## Install

```sh
npm install @acme/docs-client
```

## Usage

```ts
import { DocsClient } from '@acme/docs-client';

const client = new DocsClient({
  baseUrl: 'https://api.example.com',
  token: process.env.DOCS_TOKEN ?? '',
});

const docs = await client.listDocuments({ folderId: 'inbox', limit: 20 });
```

## Identifiers

Document and folder identifiers are accepted as either a string slug or a
numeric id, whichever the calling service already has on hand. Legacy folder
ids returned by the v1 catalog are numeric; the slug form is preferred for new
integrations but both remain supported.

```ts
await client.getDocument('q3-report');
await client.listDocuments({ folderId: 1042 });
```

## Versioning

This package follows semver. The `2.4.x` line is a feature release over `2.3.x`
and remains backward compatible with all `2.x` consumers.
