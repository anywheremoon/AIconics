MERGE_USER = """
MERGE (u:User {user_id: $user_id})
RETURN u
"""

MERGE_DEVICE = """
MERGE (d:Device {device_id: $device_id})
RETURN d
"""

MERGE_IP = """
MERGE (ip:IP {address: $ip_address})
RETURN ip
"""

MERGE_ACCOUNT = """
MERGE (a:Account {account_id: $account_id})
SET a.account_number = $account_number
RETURN a
"""


MERGE_USER_DEVICE = """
MERGE (u:User {user_id: $user_id})
MERGE (d:Device {device_id: $device_id})
MERGE (u)-[r:USES]->(d)
RETURN r
"""

MERGE_USER_IP = """
MERGE (u:User {user_id: $user_id})
MERGE (ip:IP {address: $ip_address})
MERGE (u)-[r:LOGGED_IN_FROM]->(ip)
RETURN r
"""

MERGE_USER_ACCOUNT = """
MERGE (u:User {user_id: $user_id})
MERGE (a:Account {account_id: $account_id})
SET a.account_number = $account_number
MERGE (u)-[r:OWNS]->(a)
RETURN r
"""

MERGE_TRANSFER = """
MATCH (sender:Account {account_id: $sender_account_id})
MATCH (recipient:Account {account_id: $recipient_account_id})
MERGE (sender)-[r:TRANSFERRED_TO {transaction_id: $transaction_id}]->(recipient)
SET r.amount = $amount,
    r.created_at = $created_at
RETURN r
"""

DETECT_SHARED_DEVICE = """
MATCH (u:User)-[:USES]->(d:Device)
WHERE u.user_id = $user_id
MATCH (other:User)-[:USES]->(d)
WHERE other.user_id <> u.user_id
RETURN
    d.device_id AS device_id,
    count(DISTINCT other) AS other_user_count
"""

DETECT_SHARED_IP_DEVICE = """
MATCH (u:User)-[:USES]->(d:Device)<-[:USES]-(other:User)
MATCH (u)-[:LOGGED_IN_FROM]->(ip:IP)<-[:LOGGED_IN_FROM]-(other)
WHERE u.user_id = $user_id
  AND other.user_id <> u.user_id
RETURN
    d.device_id AS device_id,
    ip.address AS ip_address,
    count(DISTINCT other) AS other_user_count
"""

DETECT_COMMON_BENEFICIARY = """
MATCH (u:User)-[:OWNS]->(sender:Account)
MATCH (sender)-[:TRANSFERRED_TO]->(recipient:Account)
MATCH (other_sender:Account)-[:TRANSFERRED_TO]->(recipient)
MATCH (other:User)-[:OWNS]->(other_sender)
WHERE u.user_id = $user_id
  AND other.user_id <> u.user_id
RETURN
    recipient.account_id AS recipient_account_id,
    recipient.account_number AS recipient_account_number,
    count(DISTINCT other) AS other_user_count
"""

DETECT_SHARED_DEVICE_COMMON_BENEFICIARY = """
MATCH (u:User)-[:USES]->(d:Device)<-[:USES]-(other:User)
WHERE u.user_id = $user_id
  AND other.user_id <> u.user_id

MATCH (u)-[:OWNS]->(sender:Account)
MATCH (other)-[:OWNS]->(other_sender:Account)

MATCH (sender)-[:TRANSFERRED_TO]->(recipient:Account)
MATCH (other_sender)-[:TRANSFERRED_TO]->(recipient)

RETURN
    d.device_id AS device_id,
    recipient.account_id AS recipient_account_id,
    recipient.account_number AS recipient_account_number,
    count(DISTINCT other) AS other_user_count
"""

GET_TRANSACTION_GRAPH = """
MATCH (sender:Account)-[t:TRANSFERRED_TO {transaction_id: $transaction_id}]->(recipient:Account)
OPTIONAL MATCH (sender_user:User)-[:OWNS]->(sender)
OPTIONAL MATCH (recipient_user:User)-[:OWNS]->(recipient)
RETURN
    t.transaction_id AS transaction_id,
    t.amount AS amount,
    t.created_at AS created_at,
    sender.account_id AS sender_account_id,
    sender.account_number AS sender_account_number,
    sender_user.user_id AS sender_user_id,
    recipient.account_id AS recipient_account_id,
    recipient.account_number AS recipient_account_number,
    recipient_user.user_id AS recipient_user_id
"""