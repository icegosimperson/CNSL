# 1. Importing the Various Modules and Libraries
import sys
import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request # pip install flask
import requests #  pip install requests
from urllib.parse import urlparse

# 2. Declaring the Class in Python
class Blockchain(object):
    difficulty_target = "0000"

    # 블록을 바이트 배열로 인코딩한 다음 해시
    def hash_block(self, block):
        block_encoded = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_encoded).hexdigest() # 해시로 변환하여 반환
    
    def __init__(self):
        self.nodes = set() # 전체 블록을 모두 저장 
        self.chain = [] # 전체 블록체인의 모든 블록을 저장
        self.current_transactions = [] # 현재 블록에 대한 트랜잭션을 임시로 저장
        genesis_hash = self.hash_block("genesis_block")
        self.append_block(hash_of_previous_block=genesis_hash, 
                          nonce=self.proof_of_work(0, genesis_hash, []))

   
    # 3. Finding the Nonce
    # 논스에 대해 0으로 시작하여 블록의 내용과 함께 논스가 난이도 목표와 일치하는 해시를 생성하는지 확인
    def proof_of_work(self, index, hash_of_previous_block, transactions):
        nonce = 0 # nonce는 0으로 시작
        # 이전 블록의 해시에 nonce를 해시
        while self.valid_proof(index, hash_of_previous_block, transactions, nonce) is False:
            nonce += 1 # 1만큼 증가시킨다. 
        return nonce

    # 블록의 내용을 해시하고 블록의 해시가 난이도 목표를 충족하는지 확인
    def valid_proof(self, index, hash_of_previous_block, transactions, nonce):
        # nonce를 포함하여 이전 블록의 해시와 내용을 포함하는 문자열 생성
        content = f'{index}{hash_of_previous_block}{transactions}{nonce}'.encode()
        content_hash = hashlib.sha256(content).hexdigest() # sha256 해시 함수 사용
        return content_hash[:len(self.difficulty_target)] == self.difficulty_target

    # 4. Appending the Block to the Blockchain
    # 새로운 블록을 만들어 블록체인에 추가
    def append_block(self, nonce, hash_of_previous_block):
        block = {
            'index': len(self.chain),
            'timestamp': time(), # 블록 추가시 현재 timestamp도 함께 추가
            'transactions': self.current_transactions,
            'nonce': nonce,
            'hash_of_previous_block': hash_of_previous_block
        }
        self.current_transactions = [] # 트랜잭션 리스트를 재설정
        self.chain.append(block) # 새로운 블록을 블록체인에 추가
        return block

    # 5. Adding Transactions
    def add_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'amount': amount,
            'recipient': recipient,
            'sender': sender,
        })
        return self.last_block['index'] + 1 # 블록체인의 마지막 블록을 반환

    @property
    def last_block(self):
        return self.chain[-1]

  
# 6. Exposing the Blockchain Class as a REST API
app = Flask(__name__) 
node_identifier = str(uuid4()).replace('-', '') # 노드의 고유한 주소 설정
blockchain = Blockchain() # 블록체인 객체 선언

# 7. Obtaining the Full Blockchain
@app.route('/blockchain', methods=['GET']) 
def full_chain():
    response = {
        'chain': blockchain.chain, 
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

# 8. Performing Mining
@app.route('/mine', methods=['GET'])
def mine_block():
    # "0"에서 이 노드가 다음 값을 생성했음을 나타냄
    blockchain.add_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
)
    # 블록체인에서 마지막 블록의 해시를 가져옵니다
    last_block_hash = blockchain.hash_block(blockchain.last_block)
    # PoW를 사용하여 추가할 새 블록의 논스를 가져옵니다
    index = len(blockchain.chain)
    nonce = blockchain.proof_of_work(index, last_block_hash,
        blockchain.current_transactions)
    # 마지막 블록을 사용하여 블록체인에 새 블록을 추가
    block = blockchain.append_block(nonce, last_block_hash)
    response = {
        'message': "New Block Mined",
        'index': block['index'],
        'hash_of_previous_block':
            block['hash_of_previous_block'],
        'nonce': block['nonce'],
        'transactions': block['transactions'],
    }
    return jsonify(response), 200

# 9. Adding Transactions
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # # 클라이언트로부터 값을 전달받습니다
    values = request.get_json()
    # # 필수 필드가 POST'ed 데이터에 있는지 확인
    required_fields = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required_fields):
        return ('Missing fields', 400)
    # 새로운 트랜잭션 생성
    index = blockchain.add_transaction(
        values['sender'],
        values['recipient'],
        values['amount']
)
    response = {'message':
        f'Transaction will be added to Block {index}'}
    return (jsonify(response), 201)

@app.route('/nodes/add_nodes', methods=['POST'])
def add_nodes():
    # get the nodes passed in from the client
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Missing node(s) info", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {
        'message': 'New nodes added',
        'nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/sync', methods=['GET'])
def sync():
    updated = blockchain.update_blockchain()
    if updated:
        response = {
            'message':
              'The blockchain has been updated to the latest',
            'blockchain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our blockchain is the latest',
            'blockchain': blockchain.chain
        }
    return jsonify(response), 200
if __name__ == '__main__':
    # 기본 포트 번호를 설정합니다 (예: 5000)
    default_port = 5000
    port = int(sys.argv[1]) if len(sys.argv) > 1 else default_port
    app.run(host='0.0.0.0', port=port)
