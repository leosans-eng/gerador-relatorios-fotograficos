# Gerador de Relatórios Fotográficos

Programa para Windows que organiza fotos de vistoria por condomínio, etapa (bloco) e anomalia, e gera automaticamente o relatório em Word (.docx) a partir do modelo padrão.

---

## Download

Baixe a versão mais recente do instalador:

**[GeradorRelatoriosFotograficos_Setup.exe](https://github.com/leosans-eng/gerador-relatorios-fotograficos/releases/latest)**

> O arquivo tem o formato `GeradorRelatoriosFotograficos_Setup_X.X.X.exe`, onde `X.X.X` é o número da versão.

---

## Requisitos do sistema

| Item | Requisito |
|------|-----------|
| Sistema operacional | Windows 10 ou superior (64 bits) |
| Espaço em disco | ~200 MB para instalação + espaço para suas fotos |
| Outros | Microsoft Word ou leitor compatível com `.docx` para abrir o relatório gerado |
| Internet | Opcional — usada apenas para verificar atualizações |

Não é necessário instalar Python nem qualquer outro programa adicional.

---

## Instalação

1. Baixe o arquivo `GeradorRelatoriosFotograficos_Setup_X.X.X.exe`.
2. Execute o instalador (clique duplo).
3. Se o Windows solicitar confirmação, clique em **Sim** ou **Executar**.
4. Siga as instruções na tela:
   - Escolha a pasta de instalação (padrão: `C:\GeradorRelatoriosFotograficos`).
   - Marque **Criar atalho na área de trabalho**, se desejar.
5. Ao final, marque **Abrir Gerador de Relatórios Fotográficos** e clique em **Concluir**.

O programa ficará disponível no Menu Iniciar e, se marcado, na área de trabalho.

---

## Primeiro uso

Ao abrir o programa pela primeira vez:

1. Clique em **Adicionar condomínio** e informe o nome do condomínio em vistoria.
2. Clique em **Adicionar etapa** para criar o primeiro bloco do relatório (ex.: *Bloco A*, *Garagem*, *Área de lazer*).
3. Adicione fotos à etapa atual (veja a seção abaixo).
4. Selecione a anomalia de cada foto e clique em **Salvar anomalia na foto**.
5. Quando terminar, clique em **Gerar relatório Word**.

O relatório será salvo na pasta **Downloads** e aberto automaticamente.

---

## Como usar

### Condomínios

- Use o seletor no topo da tela para alternar entre condomínios.
- Cada condomínio mantém suas próprias etapas, fotos e anomalias de forma independente.
- **Adicionar condomínio** / **Excluir condomínio** gerenciam a lista de projetos.

### Etapas (blocos)

As etapas representam as seções do relatório (ex.: blocos, pavimentos, áreas comuns).

- **Adicionar etapa** — cria uma nova seção.
- **Renomear etapa (Bloco) atual** — altera o nome da etapa selecionada.
- **↑ Subir etapa** / **↓ Descer etapa** — reordena as etapas no relatório.
- **Excluir etapa atual** — remove a etapa e todas as fotos dela.

### Fotos

Com uma etapa selecionada, insira fotos de três formas:

- **Arrastar e soltar** — arraste arquivos de imagem para a área indicada na tela.
- **Selecionar foto...** — escolha arquivos pelo explorador de arquivos.
- **Ctrl+V** — cole uma imagem copiada da área de transferência (ex.: captura de tela).

Formatos suportados: JPG, JPEG, PNG, BMP, GIF e WEBP.

Para cada foto:

1. Selecione-a na **Estrutura do Relatório** (painel central).
2. Escolha a anomalia no campo à direita.
3. Clique em **Salvar anomalia na foto**.

Você também pode:

- **Excluir foto** — remove a foto selecionada (tecla **Delete** também funciona).
- **↑ Subir** / **↓ Descer** — altera a ordem das fotos dentro da etapa.
- **Mover fotos selecionadas** — transfere fotos para outra etapa.

### Anomalias

O programa já inclui uma lista padrão de anomalias. Para personalizar:

- **Adicionar na lista** — inclui uma nova anomalia reutilizável.
- **Excluir da lista** — remove uma anomalia da lista (não apaga fotos já salvas).

### Gerar o relatório Word

1. Certifique-se de que **todas as fotos** possuem anomalia definida.
2. Clique em **Gerar relatório Word**.
3. Escolha onde salvar o arquivo (a pasta Downloads é sugerida por padrão).
4. O relatório será gerado e aberto automaticamente.

> O programa bloqueia a geração se houver fotos sem anomalia. A mensagem de erro indica quais fotos precisam ser corrigidas.

---

## Onde ficam seus dados

Todos os dados do seu trabalho ficam na **pasta de instalação** do programa (padrão: `C:\GeradorRelatoriosFotograficos`):

| Arquivo / pasta | Conteúdo |
|-----------------|----------|
| `condominios.json` | Condomínios, etapas, fotos e anomalias |
| `imagens\` | Cópias das fotos importadas |
| `anomalias.json` | Lista personalizada de anomalias |

O programa salva automaticamente a cada **5 minutos** e sempre que você faz alterações.

> **Importante:** Ao atualizar ou reinstalar, seus dados são preservados se você instalar na **mesma pasta**. Faça backup periódico da pasta de instalação (especialmente `condominios.json` e `imagens\`) para não perder trabalho.

---

## Atualizações

O programa verifica automaticamente se há uma versão mais recente ao iniciar (requer conexão com a internet).

Quando uma atualização estiver disponível:

1. Uma janela informará a nova versão.
2. O instalador será baixado para a pasta **Downloads**.
3. Clique em **Instalar agora** para executar o instalador.
4. Siga os passos da instalação normalmente, mantendo a **mesma pasta de instalação** para preservar seus dados.

Você também pode baixar manualmente a versão mais recente na página de [Releases](https://github.com/leosans-eng/gerador-relatorios-fotograficos/releases).

---

## Desinstalar

1. Abra **Configurações** → **Aplicativos** → **Aplicativos instalados** (ou **Painel de Controle** → **Programas e Recursos**).
2. Localize **Gerador de Relatórios Fotográficos**.
3. Clique em **Desinstalar**.

> A desinstalação remove o programa, mas **não apaga automaticamente** a pasta de instalação se ela contiver dados criados pelo usuário. Para remover tudo, exclua manualmente a pasta `C:\GeradorRelatoriosFotograficos` (ou o caminho que você escolheu na instalação) **após fazer backup**, se necessário.

---

## Problemas comuns

**O Windows bloqueou a instalação**
- Clique em **Mais informações** → **Executar assim mesmo**, ou
- Clique com o botão direito no instalador → **Propriedades** → marque **Desbloquear** → **OK**.

**"Não foi possível ler o arquivo de dados"**
- O arquivo `condominios.json` pode estar corrompido. Restaure um backup ou renomeie o arquivo para que o programa crie um novo.

**Relatório não gera — fotos sem anomalia**
- Verifique a mensagem de erro: ela lista as fotos pendentes. Selecione cada uma e salve a anomalia antes de tentar novamente.

**Arrastar fotos não funciona**
- Use **Selecionar foto...** ou **Ctrl+V** como alternativa. Reinicie o programa se o problema persistir.

**Erro ao verificar atualização**
- Verifique sua conexão com a internet. Você pode continuar usando a versão instalada normalmente e baixar atualizações manualmente pela página de Releases.

**Antivírus bloqueou o programa**
- Adicione a pasta de instalação à lista de exceções do antivírus. O instalador é gerado localmente e pode ser sinalizado incorretamente por alguns antivírus.

---

## Suporte

- **Repositório:** [github.com/leosans-eng/gerador-relatorios-fotograficos](https://github.com/leosans-eng/gerador-relatorios-fotograficos)
- **Versão atual:** 1.0.7
- **Desenvolvedor:** Léo Santos

Para reportar problemas ou solicitar melhorias, abra uma *issue* no repositório do GitHub, ou contate-me diretamente.
