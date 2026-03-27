from waitress import serve
from ecommerce.wsgi import application
import os

if __name__ == '__main__':
    print("-------------------------------------------------------")
    print(" SERVIDOR RODANDO (Waitress)")
    print(" Acesso local: http://localhost:8000")
    print(" Acesso rede:  http://<SEU_IP>:8000")
    print("-------------------------------------------------------")
    
    # 'threads=6' garante que 6 requisições simultâneas sejam processadas.
    serve(application, host='0.0.0.0', port=8000, threads=6)