from search import search_prompt

EXIT_COMMANDS = {"sair", "exit", "quit"}


def main():
    chain = search_prompt()

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return

    print("Chat iniciado. Digite 'sair' (ou Ctrl+C) para encerrar.")
    print("Faça sua pergunta:\n")

    while True:
        try:
            question = input("PERGUNTA: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAté logo!")
            break

        if not question:
            continue
        if question.lower() in EXIT_COMMANDS:
            print("Até logo!")
            break

        try:
            answer = chain.invoke(question)
        except Exception as exc:
            print(f"Erro ao processar a pergunta: {exc}\n")
            continue

        print(f"RESPOSTA: {answer.strip()}\n")
        print("---\n")


if __name__ == "__main__":
    main()
