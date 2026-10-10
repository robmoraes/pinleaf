# Feature: Pinleaf MVP - notas post-it para desktop

## Intent

Problem:
Usuários precisam registrar lembretes curtos diretamente na área de trabalho sem abrir um aplicativo pesado, trocar de contexto ou depender de conexão com a internet.

Users or stakeholders:
Usuários individuais em desktop Linux que querem notas rápidas, persistentes e sempre acessíveis.

Desired outcome:
O Pinleaf deve permitir criar, editar, mover, redimensionar e remover notas estilo post-it em janelas leves, persistindo o estado localmente entre sessões.

Non-goals:
- Sincronização entre dispositivos.
- Colaboração em tempo real.
- Contas de usuário, autenticação ou backend remoto.
- Editor rich text completo.
- Aplicativo mobile ou web.
- Sistema avançado de tags, busca global ou anexos.

## Scope

In scope:
- Aplicativo desktop nativo em Python com GTK/libadwaita.
- Criação e gerenciamento local de notas curtas.
- Persistência local das notas e de suas propriedades visuais básicas.
- Interface principal mínima para listar, criar e reabrir notas.
- Janelas de nota independentes com aparência inspirada em post-its.
- Ícone de bandeja/status para acesso rápido ao aplicativo.
- Execução direta pelo ambiente de desenvolvimento durante o MVP.
- Arquitetura preparada para suportar múltiplas formas de distribuição quando o produto tiver maturidade para distribuição.

Out of scope:
- Suporte oficial a Windows e macOS no MVP.
- Integração com calendários, notificações do sistema ou atalhos globais.
- Criptografia de notas em repouso.
- Importação/exportação em formatos externos.
- Tema customizável além das cores básicas da nota.

Assumptions:
- O MVP roda em uma sessão desktop Linux com GTK 4 e libadwaita disponíveis.
- As notas pertencem ao usuário local do sistema operacional.
- O armazenamento local usa SQLite e preserva o contrato de dados desta spec.
- O conteúdo esperado por nota é curto, orientado a lembretes, rascunhos e listas simples.

Dependencies:
- Python 3 suportado pela distribuição alvo.
- PyGObject, GTK 4 e libadwaita.
- Diretório de dados por usuário compatível com XDG, por exemplo `~/.local/share/pinleaf`.

## Behavior

1. O usuário pode iniciar o Pinleaf por um lançador desktop ou comando local.
2. Ao iniciar sem notas existentes, o aplicativo mostra uma janela principal mínima com ação para criar uma nova nota.
3. Ao iniciar com notas existentes, o aplicativo restaura as notas salvas com conteúdo, cor, tamanho, posição e estado aberto quando a plataforma permitir restaurar posição.
4. O usuário pode criar uma nova nota a partir da janela principal.
5. O usuário pode criar uma nova nota a partir do ícone de bandeja/status.
6. O usuário pode abrir ou focar a janela principal a partir do ícone de bandeja/status.
7. O usuário pode encerrar o aplicativo a partir do ícone de bandeja/status.
8. Uma nova nota começa vazia, editável imediatamente e com cor padrão amarela.
9. O usuário pode digitar e editar texto livre em uma nota.
10. Alterações de conteúdo são persistidas automaticamente sem exigir ação explícita de salvar.
11. O usuário pode fechar uma janela de nota sem excluir a nota.
12. O usuário pode reabrir uma nota fechada pela janela principal.
13. O usuário pode excluir uma nota por uma ação explícita de remoção.
14. A exclusão exige confirmação quando a nota contém texto não vazio.
15. Uma nota excluída não reaparece após reiniciar o aplicativo.
16. O usuário pode mover e redimensionar janelas de nota usando os controles normais do ambiente gráfico.
17. O aplicativo deve salvar tamanho e, quando suportado de forma confiável pelo ambiente desktop, posição da nota.
18. O usuário pode escolher pelo menos quatro cores de nota: amarelo, verde, azul e rosa.
19. A cor escolhida para uma nota é persistida entre sessões.
20. A janela principal lista notas existentes com prévia textual, cor e última atualização.
21. A prévia textual usa o início do conteúdo da nota e deve lidar com notas vazias.
22. Notas vazias são persistidas até que o usuário as exclua.
23. O aplicativo deve continuar utilizável quando uma nota não puder ser restaurada em sua posição anterior.
24. Em caso de erro ao carregar dados locais, o aplicativo deve preservar o arquivo existente sempre que possível e apresentar uma mensagem clara de falha ao usuário.
25. Em caso de erro ao salvar uma nota, o aplicativo deve informar que a alteração pode não ter sido persistida.

## Acceptance Examples

Scenario: criar e persistir uma nota
Given o Pinleaf está aberto sem notas existentes
When o usuário cria uma nova nota
And digita "Comprar cafe"
And fecha o aplicativo
And abre o Pinleaf novamente
Then a nota "Comprar cafe" aparece disponível
And seu conteúdo pode ser editado novamente

Scenario: fechar nota sem excluir
Given existe uma nota com o texto "Revisar PR"
When o usuário fecha a janela da nota
Then a nota não é excluída
And a janela principal permite reabrir essa nota

Scenario: excluir nota com confirmação
Given existe uma nota com o texto "Pagar boleto"
When o usuário solicita excluir a nota
Then o Pinleaf pede confirmação
When o usuário confirma a exclusão
Then a nota é removida da lista
And a nota não volta após reiniciar o aplicativo

Scenario: cancelar exclusão
Given existe uma nota com o texto "Ideia do projeto"
When o usuário solicita excluir a nota
And cancela a confirmação
Then a nota continua visível
And o conteúdo permanece "Ideia do projeto"

Scenario: persistir cor da nota
Given existe uma nota com cor amarela
When o usuário muda a cor para azul
And reinicia o Pinleaf
Then a nota é exibida em azul

Scenario: criar nota pelo ícone de bandeja/status
Given o Pinleaf está em execução
When o usuário aciona criar nota pelo ícone de bandeja/status
Then uma nova nota vazia é aberta
And a nota pode ser editada imediatamente

Scenario: recuperar de posição indisponível
Given existe uma nota salva com posição anterior
And o ambiente desktop não permite restaurar posição de janela
When o Pinleaf inicia
Then a nota abre em uma posição escolhida pelo gerenciador de janelas
And seu conteúdo, cor e tamanho são preservados

Scenario: erro de armazenamento local
Given o arquivo local de notas está corrompido
When o Pinleaf inicia
Then o aplicativo informa que não conseguiu carregar as notas
And não sobrescreve automaticamente o arquivo corrompido
And permite encerrar o aplicativo sem perda adicional de dados

## Data and Contracts

Inputs:
- Texto digitado pelo usuário.
- Ações de criar, abrir, fechar, excluir, confirmar exclusão e alterar cor.
- Eventos de redimensionamento e, quando disponível, posicionamento de janelas.
- Ações do ícone de bandeja/status.

Outputs:
- Janelas de nota editáveis.
- Janela principal com lista de notas e ações de gerenciamento.
- Mensagens de erro ou confirmação para eventos destrutivos e falhas de persistência.

API/schema/event changes:
- Não há API HTTP, eventos externos ou contratos de integração no MVP.

Persistence changes:
Cada nota deve persistir, no mínimo:
- Identificador estável.
- Conteúdo textual.
- Cor.
- Largura e altura da janela.
- Posição da janela quando suportada.
- Data/hora de criação.
- Data/hora da última atualização.
- Estado lógico necessário para reabrir ou listar a nota.

O armazenamento deve ser local, por usuário, e não deve exigir serviço em segundo plano ou banco remoto.

O armazenamento local do MVP deve usar SQLite. O banco deve incluir versão de esquema ou mecanismo equivalente para permitir migrações futuras.

## Quality Attributes

Security:
- O aplicativo não deve executar conteúdo das notas.
- O aplicativo não deve abrir links, comandos ou arquivos automaticamente a partir do texto digitado.
- Arquivos locais devem ser criados com permissões compatíveis com dados de usuário, evitando exposição ampla para outros usuários do sistema.

Privacy:
- O conteúdo das notas permanece local no dispositivo.
- O MVP não envia telemetria, conteúdo ou metadados para serviços externos.

Accessibility:
- Controles principais devem ser acessíveis por teclado.
- A interface deve expor rótulos acessíveis para ações como criar, excluir, mudar cor e abrir nota.
- Cores de nota não devem ser o único indicador de identidade na lista principal; a prévia textual também deve estar presente.

Performance:
- O aplicativo deve abrir a janela principal em até 2 segundos em um ambiente desktop comum com até 100 notas curtas.
- Edição de texto deve permanecer responsiva para notas com até 10.000 caracteres.
- Salvamento automático não deve bloquear perceptivelmente a digitação.

Reliability:
- O salvamento automático deve reduzir perda de dados em encerramentos normais.
- O aplicativo deve evitar sobrescrever dados existentes quando detectar erro de leitura ou formato inválido.
- Falhas em uma nota não devem impedir a listagem de outras notas válidas quando o formato de armazenamento permitir recuperação parcial.

Observability:
- Erros de leitura, escrita e inicialização devem ser registrados em log local ou stderr para diagnóstico durante desenvolvimento.
- Mensagens apresentadas ao usuário devem ser curtas e acionáveis.

## Rollout and Operations

Migration:
- O MVP começa sem migração de versões anteriores.
- O schema SQLite deve incluir versão de esquema para permitir migrações futuras.

Feature flag or configuration:
- Não há feature flags no MVP.
- Configurações de usuário ficam fora do MVP, exceto estado necessário das notas.

Rollback:
- Como não há backend, rollback significa reinstalar uma versão anterior do aplicativo.
- O schema SQLite do MVP deve ser documentado no plano técnico antes da implementação para reduzir risco de incompatibilidade.
- Durante o desenvolvimento, a forma suportada de execução é direta pelo ambiente de desenvolvimento.
- A arquitetura deve manter baixo acoplamento entre inicialização da aplicação, acesso a dados e empacotamento para permitir Flatpak, pacotes de distribuição ou outros formatos no futuro.

Monitoring:
- Não há monitoramento remoto.
- Diagnóstico depende de logs locais, stderr e mensagens de erro no aplicativo.
