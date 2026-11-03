using './main.bicep'

param location = 'polandcentral'
param vmSize = 'Standard_D4s_v5'
param githubRepoUrl = 'https://github.com/puneetg1983/sre-agent-demo'
param githubBranch = 'main'
param sreAgentName = ''
param sreAgentRg = 'rg-sreagent-demo-sreagent'
param enableSreAgent = false
