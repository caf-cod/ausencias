# Gestão de ausências · CAF

Aplicação estática para planejamento de férias, licenças e recesso da coordenação, seguindo a identidade visual do portal CAF.

## Uso
Abra `index.html` em um servidor estático ou habilite GitHub Pages em **Settings → Pages → Deploy from a branch → main → /(root)**. O endereço previsto após habilitar é https://caf-cod.github.io/ausencias/ .

1. Cadastre os colaboradores.
2. Registre o tipo e as datas de cada ausência.
3. Consulte o calendário mensal e as sobreposições em vermelho.
4. Edite ou exclua os períodos conforme necessário.

Datas inicial e final são inclusivas. As contagens são de dias corridos, sem descontar feriados ou finais de semana. Sobreposições entre pessoas diferentes são permitidas com aviso; períodos simultâneos para a mesma pessoa são bloqueados. Os filtros afetam calendário, alertas, lista e CSV. Os indicadores de disponibilidade de hoje consideram toda a equipe.

## Armazenamento
Os dados permanecem no localStorage do navegador, sem envio ao GitHub e sem sincronização entre computadores. Exportação JSON cria um backup completo; importação substitui os dados locais após confirmação. CSV exporta o recorte exibido. Limpar os dados do navegador remove os registros; mantenha backups.

Para uma base compartilhada com edição simultânea será necessário integrar autenticação e banco de dados. Esta versão não fornece esse serviço. Não registre informações de saúde ou motivos de licenças.

## Arquivos
- `index.html`: interface acessível e formulário.
- `style.css`: identidade institucional, calendário responsivo e impressão.
- `app.js`: cadastros, validação de datas, persistência, alertas, CSV e backup.

O cabeçalho utiliza o ativo institucional já publicado em caf-cod/formulario. Sem dependências de build.
