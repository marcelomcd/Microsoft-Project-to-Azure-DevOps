# Guia de Preenchimento do Microsoft Project para Integração

Este guia explica como preencher corretamente o arquivo Microsoft Project (`.mpp`) para que a integração com o Azure DevOps funcione adequadamente.

## 📋 Índice

1. [Estrutura Básica](#estrutura-basica)
2. [Campos Importantes](#campos-importantes)
3. [Status das Tarefas](#status-das-tarefas)
4. [Recursos e Responsáveis](#recursos-e-responsaveis)
5. [Horas de Trabalho](#horas-de-trabalho)
6. [Boas Práticas](#boas-praticas)

---

## <a id="estrutura-basica"></a>🏗️ Estrutura Básica

### Hierarquia de Tarefas

O Microsoft Project deve seguir esta estrutura:

```
Feature (não é criada pelo script)
  └── User Story (tarefa sem recurso atribuído)
      └── Task (tarefa com recurso atribuído)
```

### Regras de Identificação

- **User Story**: Tarefa que **NÃO** possui recurso atribuído no campo "Nomes dos recursos"
- **Task**: Tarefa que **POSSUI** recurso atribuído no campo "Nomes dos recursos"

---

## <a id="campos-importantes"></a>📝 Campos Importantes

### Campos Obrigatórios

| Campo no MPP | Descrição | O que é sincronizado |
|--------------|-----------|----------------------|
| **Nome da Tarefa** | Título da tarefa | `System.Title` no Azure DevOps |
| **Data de Início** | Data de início da tarefa | `Microsoft.VSTS.Scheduling.StartDate` |
| **Data de Conclusão** | Data de término da tarefa | `Microsoft.VSTS.Scheduling.TargetDate` |

### Campos Opcionais

| Campo no MPP | Descrição | O que é sincronizado |
|--------------|-----------|----------------------|
| **Notas** | Descrição/observações | `System.Description` |
| **Prioridade** | Nível de prioridade | `Microsoft.VSTS.Common.Priority` |
| **Trabalho** | Horas estimadas (em segundos) | `Microsoft.VSTS.Scheduling.OriginalEstimate` (apenas Tasks) |
| **% Concluída** | Porcentagem de conclusão | **NÃO é sincronizado** (apenas para referência) |

---

## <a id="status-das-tarefas"></a>🔄 Status das Tarefas

### Como o Status é Calculado

O sistema calcula automaticamente o status da tarefa baseado em:

1. **% Concluída = 100%** ou possui **Data de Conclusão Real** → Status: **"Concluída"**
2. **Data de Início no futuro** → Status: **"Tarefa Futura"**
3. **Atraso detectado** (variação de término > 0 ou data de término no passado) → Status: **"Atrasada"**
4. **Caso contrário** → Status: **"No Prazo"**

### Mapeamento para Azure DevOps

| Status no MPP | Status no Azure DevOps |
|---------------|----------------------|
| **Concluída** | `Closed` |
| **Tarefa Futura** | `New` |
| **No Prazo** ou **Atrasada** | `Active` |
| **Removed** | Não processado (ignorado) |

### ⚠️ Proteção de Status

**IMPORTANTE**: Se uma Task no Azure DevOps já estiver com status:
- `Closed`
- `Removed`
- `Resolved`

O sistema **NÃO alterará** esse status, mesmo que o arquivo `.mpp` tenha outro valor. Isso evita reabrir tarefas que já foram concluídas, removidas ou resolvidas.

---

## <a id="recursos-e-responsaveis"></a>👤 Recursos e Responsáveis

### Atribuição de Recursos

- **Com Recurso**: Tarefa será criada como **Task** no Azure DevOps
- **Sem Recurso**: Tarefa será criada como **User Story** no Azure DevOps

### Regra Especial: Recurso "Cliente"

Se o recurso contém a palavra **"Cliente"** (ex: "Cliente", "Cliente [1]", "Cliente [2]"), o campo **Responsável** no Azure DevOps será deixado em branco ("No one selected").

### Mapeamento de Recursos

O sistema utiliza um mapeamento de recursos para emails. Certifique-se de que os nomes dos recursos no Microsoft Project correspondem aos nomes configurados no sistema.

---

## <a id="horas-de-trabalho"></a>⏱️ Horas de Trabalho

### Campo "Trabalho"

- **Onde preencher**: Campo "Trabalho" no Microsoft Project
- **Formato**: O Microsoft Project armazena em segundos, mas o sistema converte automaticamente para horas
- **Onde vai**: Campo `Original Estimate` no Azure DevOps (apenas para Tasks)
- **Exemplos**:
  - 8 horas = 28800 segundos → 8.0 horas no Azure DevOps
  - 4 horas = 14400 segundos → 4.0 horas no Azure DevOps

### ⚠️ Horas Consumidas (Completed Work)

**IMPORTANTE**: O campo **"Horas Consumidas"** (`Completed Work`) no Azure DevOps **NÃO é preenchido** automaticamente pelo script. Este campo deve ser gerenciado manualmente no Azure DevOps.

O campo **"% Concluída"** do Microsoft Project é usado apenas para calcular o status da tarefa, mas **não** para preencher horas consumidas.

---

## <a id="boas-praticas"></a>✅ Boas Práticas

### 1. Nomenclatura de Tarefas

- Use títulos claros e descritivos
- Evite caracteres especiais que possam causar problemas
- Mantenha consistência na nomenclatura

### 2. Estrutura Hierárquica

- Organize User Stories e Tasks de forma lógica
- Mantenha a hierarquia clara (User Story → Task)
- Evite tarefas órfãs (sem parent)

### 3. Datas

- Preencha sempre as datas de início e término
- Certifique-se de que as datas estão corretas
- Evite datas no passado para tarefas futuras

### 4. Recursos

- Atribua recursos apenas às Tasks (não às User Stories)
- Use nomes de recursos consistentes
- Verifique o mapeamento de recursos antes de usar

### 5. Status

- Deixe o sistema calcular o status automaticamente
- Não tente forçar status manualmente (o sistema recalcula)
- Lembre-se: tarefas com status `Closed`, `Removed` ou `Resolved` no Azure DevOps não terão o status alterado

### 6. Horas

- Preencha o campo "Trabalho" para Tasks que precisam de estimativa
- Use valores realistas (em horas)
- Lembre-se: apenas Tasks recebem horas (User Stories não)

---

## 📌 Resumo Rápido

| Item | Regra |
|------|-------|
| **User Story** | Tarefa sem recurso atribuído |
| **Task** | Tarefa com recurso atribuído |
| **Status** | Calculado automaticamente pelo sistema |
| **Horas** | Campo "Trabalho" → `Original Estimate` (apenas Tasks) |
| **Horas Consumidas** | **NÃO** é preenchido pelo script |
| **Status Protegido** | `Closed`, `Removed`, `Resolved` não são alterados |
| **Recurso "Cliente"** | Deixa responsável em branco |

---

## ❓ Dúvidas Frequentes

### O campo "% Concluída" preenche horas consumidas?

**Não**. O campo "% Concluída" é usado apenas para calcular o status da tarefa. O campo "Horas Consumidas" (`Completed Work`) no Azure DevOps deve ser preenchido manualmente.

### Posso alterar o status de uma tarefa que está "Closed" no Azure DevOps?

**Não automaticamente**. Se uma tarefa está `Closed`, `Removed` ou `Resolved` no Azure DevOps, o sistema não alterará esse status, mesmo que o arquivo `.mpp` tenha outro valor. Isso é uma proteção para evitar reabrir tarefas concluídas.

### User Stories recebem horas de trabalho?

**Não**. Apenas Tasks recebem o campo `Original Estimate` preenchido com as horas do campo "Trabalho" do Microsoft Project.

### Como criar uma User Story?

Simplesmente **não atribua nenhum recurso** à tarefa no Microsoft Project. Tarefas sem recurso são automaticamente criadas como User Stories no Azure DevOps.

---

**Última atualização**: Dezembro 2024
