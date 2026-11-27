> Source: https://github.com/nestjs/docs.nestjs.com/blob/master/content/tutorials/overview.md

# Node.js backend tutorials

Step-by-step tutorials that build complete Node.js backends in TypeScript with NestJS: REST and GraphQL APIs, MongoDB, microservices, MCP servers and AI.

Each tutorial builds one application of the kind teams actually ship, from an empty project to code you could deploy, and links to the chapters of this documentation for the details of each part. They use the current APIs: validation with Zod schemas, the Node adapter, [`@nestjs/authentication`](https://docs.nestjs.com/security/authentication), and Drizzle on PostgreSQL, or Mongoose on MongoDB. Every listing comes from an application that was built and tested, and every output on the pages comes from running it. Each finished application is also on GitHub, as `nestjs/example-<slug>`: for example [nestjs/example-rest-api-jwt-authentication](https://github.com/nestjs/example-rest-api-jwt-authentication).

Most of a backend is ordinary CRUD, so the tutorials spend their time on the parts that aren't: what happens when two requests arrive at once, when a client retries, or when a token is stolen. Each one tests those guarantees against a real database, not a mock.

## Where to start

Start with [Build a REST API with JWT authentication in Node.js](https://docs.nestjs.com/tutorials/rest-api-jwt-authentication). It begins with a single file, and adds request validation, a PostgreSQL database, sign-up with access and refresh tokens, rate limiting, security headers, an OpenAPI document, health checks, JSON logs and end-to-end tests.

Most of the other tutorials start from its finished application, and add what their task needs. [Accept payments with webhooks](https://docs.nestjs.com/tutorials/payments-webhooks) continues the e-commerce backend instead.

If you use MongoDB, start with [Build a CRUD REST API with Node.js and MongoDB](https://docs.nestjs.com/tutorials/mongodb-crud-api) instead. It stands on its own, starting from an empty project.

## The tutorials

| Tutorial | What you build | The hard part it solves |
| --- | --- | --- |
| [REST API with JWT authentication](https://docs.nestjs.com/tutorials/rest-api-jwt-authentication) | A notes API with sign-up, access and refresh tokens, PostgreSQL, OpenAPI, health checks and tests | Refresh-token reuse, sign-in timing that reveals accounts, writes that race |
| [Google login](https://docs.nestjs.com/tutorials/google-login) | Sign in with Google for the notes API: ID tokens from the web and mobile apps, exchanged for the API's own JWTs, and connected accounts | Never handing an account to whoever signed up with its email first, and one account however many first sign-ins race |
| [CRUD REST API with MongoDB](https://docs.nestjs.com/tutorials/mongodb-crud-api) | A product catalog on MongoDB through Mongoose: create, list, get, partial update and delete | Malformed ids and duplicate SKUs that aren't 500s, operator injection, pages that never repeat or skip a product, and edits that don't overwrite each other |
| [GraphQL API](https://docs.nestjs.com/tutorials/graphql-api) | A GraphQL API for a blog: posts with drafts, comments, cursor pagination, sign-in mutations and a comment subscription, on Apollo and PostgreSQL | N+1 queries batched per request, drafts and emails hidden on every path, error codes a client can act on, and a WebSocket held to the same checks as HTTP |
| [E-commerce backend](https://docs.nestjs.com/tutorials/ecommerce-backend) | A catalog that only staff edit, carts, checkout, cancelling and shipping | Never selling more than is in stock, however many customers check out at once |
| [Multi-tenant SaaS backend](https://docs.nestjs.com/tutorials/multi-tenant-saas) | Organizations, roles, email invitations, tenant-owned projects, an audit log | Keeping every query inside its tenant, and never losing an organization's last owner |
| [Project-management API](https://docs.nestjs.com/tutorials/project-management-api) | Projects, tasks and comments, live updates over Server-Sent Events, due-date reminders | Permissions checked record by record, and status changes that don't overwrite each other |
| [Real-time chat backend](https://docs.nestjs.com/tutorials/realtime-chat) | A WebSocket gateway with rooms, message history, presence and typing indicators | Authenticating sockets, and checking membership on every message |
| [Booking system](https://docs.nestjs.com/tutorials/booking-system) | Bookable resources, free slots per day, bookings and cancellations | No double bookings, guaranteed by the database |
| [Emails and background jobs](https://docs.nestjs.com/tutorials/background-jobs) | A welcome email and a daily digest, sent from a BullMQ queue | Emails that are never lost or sent twice, and scheduled jobs that run on one instance |
| [File upload service](https://docs.nestjs.com/tutorials/file-uploads) | Uploads, downloads, expiring links and per-user quotas, on disk or S3 | Checking type and size while streaming, and quotas under concurrent uploads |
| [Payments with webhooks](https://docs.nestjs.com/tutorials/payments-webhooks) | Payments for the e-commerce backend, confirmed by the provider's signed webhooks | Applying each payment event exactly once, in any order |
| [AI chat backend](https://docs.nestjs.com/tutorials/ai-chat-backend) | A chatbot over the user's notes, with tools and answers streamed to the browser | Tools that see only the user's own data, and stopping the model when the browser goes away |
| [MCP server](https://docs.nestjs.com/tutorials/mcp-server) | An MCP server for a helpdesk: tools to search and reply to tickets, tickets as resources, a reply prompt, over Streamable HTTP and stdio | OAuth access tokens verified as a resource server, one team's token never reaching another team's tickets, and a write scope the model can't get around |
| [Microservices with RabbitMQ](https://docs.nestjs.com/tutorials/microservices-rabbitmq) | An orders API and a fulfillment worker in one monorepo, talking over RabbitMQ with events and request-response | Messages never lost to a crash or a broker outage, poison messages dead-lettered, each event handled once |

## What you need

- Node.js 22 or later, and the [Nest CLI](https://docs.nestjs.com/cli/overview).
- Docker, to run PostgreSQL locally, MongoDB, RabbitMQ and Redis for the tutorials that use them.
- `curl`, to try the endpoints. Each tutorial also serves its OpenAPI document with Swagger UI.

The AI chat tutorial runs without a model provider's API key: it uses a scripted model, and shows the configuration for a real one.

## More

- Deciding whether Nest fits your project: [Nest vs Fastify, Express and Hono](https://docs.nestjs.com/faq/nest-vs-fastify-express-hono).
- Moving an existing application: [Migrating from Express](https://docs.nestjs.com/migrating/express) and [Migrating from Fastify](https://docs.nestjs.com/migrating/fastify).
- Seeing what your API does in production: [NestJS Observe](https://docs.nestjs.com/observability/overview).
