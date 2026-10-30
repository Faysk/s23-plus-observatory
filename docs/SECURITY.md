# Segurança

- Somente leitura pela interface HTTP; **nenhuma chamada executa comandos recebidos do cliente**.
- API em loopback, acesso remoto por SSH com fingerprint validada e preferencialmente autenticação por chave ED25519.
- Não abrir 8783 nem 8022 para a Internet; não fazer NAT/port forwarding público.
- SQLite, logs, backups, payloads reais e capturas não devem ser publicados no GitHub.
- O HTTP não tem autenticação própria; `--unsafe-lan` **não** deve ser usado em redes partilhadas.
- Não instalar plugins Android ou solicitar permissões que não sejam necessárias; `Termux:API` é opcional.
- Na ausência de um sensor, retornar `null`; nunca explorar dados de apps sem autorização.
- Sem analytics, CDNs ou dependências JS externas.
