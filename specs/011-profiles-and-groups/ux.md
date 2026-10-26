# UX de perfis e grupos

Direção de UX aceita para a versão em desenvolvimento 0.8.0. Os comportamentos
confirmados na conversa estão em [spec.md](spec.md). Migração, exclusão,
criação e busca estão definidos; o desenho técnico está em [plan.md](plan.md).

## Perfil na barra de título

Recomendo um botão com o nome do perfil e uma seta, no centro da barra de título.
Um clique abre uma lista compacta ancorada no próprio botão. Escolher outro
perfil fecha a lista e restaura seu último grupo ativo.

Exemplo do título: **Seventh ▾**, com **LGPD** como subtítulo. O nome da janela
continua identificando Pinleaf para o sistema. O botão tem descrição acessível
como “Trocar perfil, Seventh”. Nomes longos usam reticências e descrição completa.

O menu mostra Seventh, Freelancer e Pessoal, com uma marca no perfil atual.
Abaixo ficam **Novo perfil…** e **Gerenciar perfis…**. O gerenciamento contém
criação, renomeação e exclusão de perfis.

Isso mantém a troca cotidiana em dois cliques, deixando os formulários em um
fluxo secundário. Uma janela própria para cada troca acrescentaria uma etapa a
uma navegação frequente. Uma lista suspensa simples também funciona, mas o
botão com menu acomoda seleção e ações de gerenciamento no mesmo ponto.

A recomendação se apoia no uso de seletores compactos em espaços reduzidos e
no limite de controles da barra de título do
[GNOME HIG sobre listas suspensas](https://developer.gnome.org/hig/patterns/controls/drop-downs.html) e
[barras de título](https://developer.gnome.org/hig/patterns/containers/header-bars.html).
O uso específico para perfis é uma decisão proposta para o Pinleaf.

## Grupos no lugar da lista atual

A área central passa a mostrar uma lista de grupos expansíveis. Cada seção tem:

- nome e quantidade de notas;
- ação **Ativar**, ou indicação textual **Ativo**;
- seta para expandir/recolher;
- menu com **Renomear grupo…** e **Excluir grupo…**, quando aplicável;
- notas do grupo na área expandida.

**Geral** aparece primeiro; os demais grupos seguem ordem alfabética. Dentro
de cada grupo, as notas mantêm a ordem atual, pelas mais recentes em criação.
Uma ação **Novo grupo…** fica acima da lista, fora da barra de título.

O [Adw.ExpanderRow](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.5/class.ExpanderRow.html)
oferece a expansão de linhas e conteúdo abaixo delas. Os métodos necessários
foram conferidos no GTK 4.14/libadwaita 1.5 instalado. A composição permite a
sanfona proposta no alvo Ubuntu 24.04 sem acrescentar outra biblioteca.

Recomendo permitir várias seções expandidas. Você pode consultar Agenda enquanto
trabalha em LGPD. O grupo ativo se expande quando é ativado, mas pode ser
recolhido depois. Um único painel de rolagem atende a lista inteira; cada grupo
não ganha uma rolagem própria.

## Expandir e ativar são ações diferentes

**Expandir** mostra a lista de notas do grupo no painel. **Ativar** troca o
conjunto de post-its do desktop. Recolher um grupo controla apenas a lista.

Essa separação permite organizar e consultar outros projetos enquanto o
contexto de trabalho continua estável. O texto **Ativo**, no cabeçalho do grupo,
e o subtítulo da barra de título mantêm o destino das novas notas evidente.

Não recomendo switches independentes nos grupos: a escolha é exclusiva, e um
switch sugere uma configuração ligada/desligada. Para esta proposta, o botão
**Ativar** e o estado **Ativo** comunicam melhor a ação. A natureza de
liga/desliga dos switches é descrita no
[GNOME HIG](https://developer.gnome.org/hig/patterns/controls/switches.html).

Ativar um grupo vazio mostra o estado **Nenhuma nota neste grupo**, com
**Criar nota**. Um grupo com notas apenas ocultas mantém essas notas na lista,
riscadas; o desktop fica sem post-its desse grupo.

## Notas e ações

As linhas mantêm cor, prévia e data da nota. As ocultas continuam riscadas e
recebem descrição acessível “Nota oculta”. As configurações de perfil/grupo
ficam no painel, sem identificadores adicionais nos post-its.

No grupo ativo, a ativação da linha abre a nota. O menu da linha oferece
**Abrir**, **Ocultar** quando aberta, **Mover para…** e **Excluir…**.
Ocultar e excluir conservam os comportamentos e confirmações atuais.

Em um grupo inativo, a linha funciona como consulta; sua ação de abertura fica
explicitamente no menu como **Ativar e abrir**. Não se troca o desktop ao
expandir ou apenas consultar a lista. O nome acessível da ação inclui o grupo
de destino. A busca fora do contexto usa essa mesma ação.

## Criar e renomear

**Novo perfil…** abre um formulário com nome e botão **Criar e ativar**. A
operação cria o perfil, seu Geral e o seleciona. **Novo grupo…** usa o mesmo
princípio dentro do perfil atual. O rótulo final explicita a troca de contexto.

Renomear usa formulário curto com **Cancelar** e **Salvar**. Geral é identificado
como grupo permanente, sem renomeação ou exclusão isolada. Validação aparece junto ao
campo; cancelar mantém o contexto e devolve o foco ao controle de origem.

## Mover uma nota

**Mover para…** abre um diálogo com dois seletores:

1. **Perfil**: Seventh, Freelancer, Pessoal etc.
2. **Grupo**: grupos pertencentes ao perfil escolhido, incluindo Geral.

O rodapé mostra o destino completo, por exemplo **Pessoal / Financeiro**, e
oferece **Cancelar** e **Mover**. O destino atual é indicado, com a confirmação
indisponível até a escolha de outro grupo.

Mover mantém o grupo ativo. Uma nota aberta que sai do contexto ativo deixa
esse desktop e reaparece ao ativar o destino. Uma nota oculta permanece oculta,
inclusive se o destino for o grupo ativo. Falhas de salvamento preservam a
nota e o formulário para uma nova tentativa.

## Excluir um grupo ou perfil

**Excluir grupo…** fica no menu do grupo; **Excluir perfil…**, no gerenciamento
de perfis. O formulário identifica o que será excluído e mostra quantas notas
serão afetadas, incluindo as ocultas. Excluir um perfil abrange todos os seus
grupos; o resumo informa também essa quantidade.

Para um contêiner com notas, há duas escolhas explícitas:

1. **Mover as notas**: opção inicial, com os seletores Perfil e Grupo usados no
   movimento individual. O destino deve ficar fora do grupo/perfil excluído.
   Todas as notas vão para esse único grupo; os grupos de origem não são copiados.
2. **Excluir todas as notas**: remove as notas usando o comportamento atual de
   exclusão. Essa opção não vem marcada e a ação final recebe aparência destrutiva.

O resumo mostra o destino completo e qual contexto ficará ativo. Ao excluir o
grupo ativo, passa a valer Geral no mesmo perfil. Ao excluir o perfil ativo e
mover as notas, o grupo de destino fica ativo. Se as notas forem excluídas,
o formulário pede o perfil que ficará ativo e informa seu último grupo válido.
Excluir um contêiner inativo mantém o contexto atual.

O botão final usa **Excluir grupo e mover notas**, **Excluir perfil e mover
notas** ou **Excluir perfil/grupo e N notas**, conforme a escolha. **Cancelar**
é a resposta padrão. Um contêiner sem notas não excluídas usa a confirmação simples,
sem exigir destino de notas; a escolha do próximo perfil continua necessária
se o perfil ativo for excluído.
Notas já excluídas permanecem excluídas nesse caso, sem exigir um destino.

Geral não oferece exclusão isolada. No último perfil, a exclusão fica
indisponível com a explicação **Crie outro perfil antes de excluir este**.
Cancelar ou falhar um salvamento mantém as notas e o contexto atual. Se a
quantidade afetada mudar antes da confirmação, o resumo precisa ser revisto.

## Busca

A busca permanece acima da lista. Quando há texto, uma escolha de escopo
oferece **Grupo ativo**, **Perfil atual** e **Todos os perfis**. O padrão
é Grupo ativo.

No perfil atual, os resultados aparecem em seus grupos, temporariamente
expandidos. Na busca global, uma lista de resultados mostra o caminho de cada
nota, como **Freelancer / Empresa X - DevOps**. Essa visão não acrescenta um
terceiro nível de sanfonas. Limpar a busca recupera a expansão anterior.

Busca e escopo não mudam o contexto do desktop. Abrir um resultado externo usa
**Ativar e abrir**. Ao trocar de contexto, a busca é limpa e o escopo volta para
Grupo ativo; essa regra evita que um filtro antigo esconda as notas do novo
projeto.

## Componentes e limites

| Necessidade | Composição disponível | Decisão de UX |
| --- | --- | --- |
| Perfil no título | Adw.HeaderBar com Gtk.MenuButton e Gtk.Popover | Troca compacta; formulários no gerenciamento |
| Grupos em sanfona | Adw.ExpanderRow em lista com uma rolagem externa | Expandir e ativar separados |
| Ações das notas | Linhas e menus do painel | Destino explícito nas ações que trocam contexto |
| Destino de movimento | Diálogo com seletores de perfil e grupo | Mostrar caminho antes de confirmar |
| Exclusão de perfil/grupo | Formulário com escolha de destino ou exclusão e resumo final | Cancelar por padrão; impacto explícito |
| General localizado | Identidade permanente e rótulo traduzido | General em inglês, Geral em pt-BR |

O [Gtk.MenuButton](https://docs.gtk.org/gtk4/class.MenuButton.html) aceita um
popover; o
[GNOME HIG sobre popovers](https://developer.gnome.org/hig/patterns/containers/popovers.html) fundamenta
seu uso para conteúdo e ações ancoradas. As APIs usadas na proposta foram
conferidas localmente; não se depende de componentes posteriores à libadwaita 1.5.

ExpanderRow resolve a apresentação, mas exclusividade do grupo ativo, seleção
de notas, foco e restauração de estado ainda são comportamentos da aplicação.
Essa composição deve ser validada com teclado/leitor de tela e muitos grupos
durante a futura implementação.

## Prévia e revisão

A [prévia interativa](profiles-and-groups.html) representa seleção de perfil,
expansão, ativação, busca, movimento e estado aberto/oculto com dados fictícios.
Seus controles exploram a proposta; não alteram notas do Pinleaf. A prévia
anterior não demonstra o fluxo de exclusão, especificado acima.

As alternativas de design permitem comparar expansão independente com ativação
ao expandir, e várias seções abertas com sanfona exclusiva. O padrão proposto é
expansão independente e várias seções abertas, conforme a direção aceita.

A migração inicial coloca todas as notas em **Pessoal / Geral**. A implementação
GTK segue as [tasks](tasks.md) e o [plano técnico](plan.md). As verificações e
limitações observadas estão no [registro de execução](execution-2026-10-10.md);
o protótipo HTML permanece como referência da proposta, sem simular exclusão.
