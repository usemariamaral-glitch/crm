"""
Gerador de senha segura para o CRM Mari Amaral.
Execute: python gerar_senha.py

Cole o resultado no arquivo .streamlit/secrets.toml.
"""
import hashlib
import getpass

SALT = "crm_mari_2024"

def hash_senha(senha: str) -> str:
    return "sha256:" + hashlib.sha256(f"{SALT}{senha}".encode()).hexdigest()

print("=" * 52)
print("   Gerador de Usuário — CRM Mari Amaral")
print("=" * 52)
print()

usuario  = input("Nome de usuário (sem espaços, ex: mari): ").strip().lower()
nome     = input("Nome completo (ex: Mari Amaral): ").strip()
email    = input("E-mail: ").strip()
senha    = getpass.getpass("Senha: ")
confirma = getpass.getpass("Confirme a senha: ")

if senha != confirma:
    print("\n❌ As senhas não coincidem. Tente novamente.")
    exit(1)

hashed = hash_senha(senha)

print()
print("✅ Pronto! Adicione o bloco abaixo ao arquivo .streamlit/secrets.toml:")
print()
print(f"[users.{usuario}]")
print(f'name     = "{nome}"')
print(f'email    = "{email}"')
print(f'password = "{hashed}"')
print()
