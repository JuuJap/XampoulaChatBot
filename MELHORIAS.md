# Resumo das melhorias — v2.0

1. **Arquitetura simplificada:** um único servidor FastAPI entrega frontend + API.
2. **Sem CORS no desenvolvimento local:** o navegador e a API usam a mesma origem.
3. **Gemini atualizado:** Interactions API e modelo configurável, padrão `gemini-3.8-flash`.
4. **Contexto correto:** os passos completos retornados pelo Gemini são guardados em memória, como recomendado para `store=False`.
5. **Menos exposição:** a chave não está no JavaScript e não vai no ZIP como segredo real.
6. **Banco real:** respostas salvas entram no MySQL; chat completo não é persistido.
7. **Banco relacional:** `sessoes` + `respostas_salvas` com chave estrangeira e `ON DELETE CASCADE`.
8. **Limpeza de sessão:** fechamento da aba tenta apagar a sessão e há limpeza automática de sessões antigas.
9. **Tratamento de erros:** mensagens claras para 429, chave inválida, modelo indisponível e MySQL offline.
10. **Interface:** status do sistema, contador, animação de resposta, salvar/excluir/limpar e layout responsivo.
11. **Personalidade separada:** `system_prompt.txt` pode ser editado sem mexer na lógica Python.
12. **Execução mais fácil:** `CONFIGURAR.bat` e `INICIAR.bat`.
