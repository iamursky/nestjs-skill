> Source: https://github.com/nestjs/docs.nestjs.com/blob/master/content/microservices/interceptors.md

# Interceptors

Microservice interceptors work the same way as [regular interceptors](https://docs.nestjs.com/interceptors). The following example uses a manually instantiated method-scoped interceptor. As with HTTP-based applications, you can also use controller-scoped interceptors (i.e., prefix the controller class with a `@UseInterceptors()` decorator).

```typescript
@UseInterceptors(new TransformInterceptor())
@MessagePattern({ cmd: 'sum' })
accumulate(data: number[]): number {
  return (data || []).reduce((a, b) => a + b);
}
```

> info **Hint** Global interceptors registered on the main HTTP application don't apply to microservices connected to a [hybrid application](https://docs.nestjs.com/faq/hybrid-application) unless you set the `inheritAppConfig` option. See [sharing configuration](https://docs.nestjs.com/faq/hybrid-application#sharing-configuration).
