param aksName string
param githubRepoUrl string
param githubBranch string
param substitutes object

resource aks 'Microsoft.ContainerService/managedClusters@2025-02-01' existing = { name: aksName }
resource extension 'Microsoft.KubernetesConfiguration/extensions@2023-05-01' = {
  scope: aks
  name: 'flux'
  properties: {
    extensionType: 'microsoft.flux'
    autoUpgradeMinorVersion: true
    releaseTrain: 'Stable'
    scope: { cluster: { releaseNamespace: 'flux-system' } }
    configurationSettings: { 'multiTenancy.enforce': 'false' }
  }
}
resource config 'Microsoft.KubernetesConfiguration/fluxConfigurations@2024-11-01' = {
  scope: aks
  name: 'store'
  dependsOn: [extension]
  properties: {
    scope: 'cluster'
    namespace: 'flux-system'
    sourceKind: 'GitRepository'
    gitRepository: {
      url: githubRepoUrl
      repositoryRef: { branch: githubBranch }
      syncIntervalInSeconds: 60
      timeoutInSeconds: 120
    }
    kustomizations: {
      store: {
        path: './app'
        syncIntervalInSeconds: 60
        retryIntervalInSeconds: 30
        timeoutInSeconds: 600
        prune: true
        force: false
        wait: true
        postBuild: { substitute: substitutes }
      }
    }
  }
}
