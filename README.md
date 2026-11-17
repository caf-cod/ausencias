# Gestão de ausências · CAF

Calendário mensal para planejamento de férias, licenças e recesso da coordenação.

## Base compartilhada

A aplicação consulta automaticamente `dados/ausencias.json` na branch `main`, pela API do GitHub e sem cache, em cada abertura. O arquivo inicial é o backup fornecido em 17/11/2026. Ninguém precisa conectar uma conta para consultar a base pública.

As alterações na tela ficam pendentes até clicar em **Salvar alterações**. Esse botão atualiza o mesmo arquivo no GitHub e cria um commit. Os próximos acessos carregam a atualização. Em abas que já estavam abertas, use **Recarregar** para consultar a nova versão.

Para salvar:

1. Uma conta com permissão de escrita no repositório cria um fine-grained personal access token no GitHub.
2. Selecione o proprietário caf-cod e apenas o repositório ausencias, concedendo `Contents: Read and write`. Configure uma validade limitada.
3. Na aplicação, clique em **Conectar ao GitHub**, informe o token e clique em **Salvar alterações** após editar.

O token fica apenas em memória na aba e vai diretamente para api.github.com. Não é armazenado em localStorage, backup ou código. Recarregar, fechar a página ou clicar em Desconectar remove a conexão. Não compartilhe tokens: cada editor deve usar seu próprio acesso autorizado. Nenhuma credencial é distribuída com a aplicação.

Antes de salvar, a aplicação confere o SHA da base que carregou. Se outra pessoa atualizou o arquivo, bloqueia a sobrescrita: exporte seu backup, recarregue e reaplique as alterações. O SHA também é enviado na gravação para proteger contra atualizações concorrentes durante o envio. Se houver erro ou resposta incerta, confira a versão remota antes de reenviar.

Alterações pendentes permanecem somente na aba atual. Exporte JSON antes de fechar se não puder salvar. O navegador exibe um aviso de saída quando possível. A importação de backup altera a versão em edição; ela só será compartilhada após salvar no GitHub.

## Calendário

Cadastre colaboradores e períodos. As datas inicial e final são inclusivas, com contagem de dias corridos. Ausências de pessoas diferentes podem coincidir e aparecem nos alertas. Períodos simultâneos da mesma pessoa são bloqueados no formulário.

Filtros afetam calendário, lista, sobreposições e CSV. Os indicadores de disponibilidade de hoje consideram toda a equipe. CSV exporta o recorte; JSON exporta toda a base em edição.

## Publicação

Aplicação estática sem build: GitHub Pages → Deploy from a branch → main → /(root). Arquivos: `index.html`, `style.css`, `app.js` e `dados/ausencias.json`.

O repositório e a base são públicos. Não registre motivos de licenças, informações de saúde ou outros dados restritos. Versões anteriores do arquivo continuam no histórico de commits do GitHub.
