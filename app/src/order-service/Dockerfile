FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY order-service.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /out --no-restore
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /out .
USER app
ENV ASPNETCORE_HTTP_PORTS=3000
EXPOSE 3000
ENTRYPOINT ["dotnet", "order-service.dll"]
