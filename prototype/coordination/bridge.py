"""Local, file-based mailbox for Codex and Gemini. Standard library only.

Messages are data, never executed. No API credentials, network, or daemon.
Calling inbox does not acknowledge a message; recipients acknowledge explicitly.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

AGENTS = ('codex', 'gemini')
STATES = ('paused', 'waiting', 'working', 'ready-for-review', 'blocked', 'done')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


class Bridge:
    def __init__(self, root):
        self.root = Path(root)

    def write(self, folder, name, data):
        directory = self.root / folder
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (name + '.json')
        temporary = directory / ('.' + name + '.' + uuid4().hex + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def agent(value):
        if value not in AGENTS:
            raise ValueError('Agent must be codex or gemini.')
        return value

    def message(self, message_id):
        if not re.fullmatch(r'msg_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{32}', message_id):
            raise ValueError('Invalid message ID; use the ID returned by send/inbox.')
        path = self.root / 'messages' / (message_id + '.json')
        if not path.is_file():
            raise ValueError('Message not found: ' + message_id)
        return json.loads(path.read_text(encoding='utf-8'))

    def send(self, sender, recipient, subject, body, reply_to=None):
        self.agent(sender)
        self.agent(recipient)
        if sender == recipient:
            raise ValueError('Sender and recipient must differ.')
        if not subject.strip() or not body.strip():
            raise ValueError('Subject and body must not be empty.')
        if reply_to:
            previous = self.message(reply_to)
            if previous['to'] != sender or previous['from'] != recipient:
                raise ValueError('Reply must reverse the participants of the original message.')
        message_id = 'msg_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex
        data = {'id': message_id, 'from': sender, 'to': recipient,
                'created_utc': now(), 'subject': subject, 'body': body,
                'reply_to': reply_to}
        self.write('messages', message_id, data)
        return data

    def inbox(self, agent, include_acknowledged=False):
        self.agent(agent)
        result = []
        for path in sorted((self.root / 'messages').glob('msg_*.json')):
            item = json.loads(path.read_text(encoding='utf-8'))
            if item['to'] != agent:
                continue
            receipt = self.root / 'receipts' / (item['id'] + '.json')
            item['acknowledged'] = receipt.is_file()
            if item['acknowledged']:
                item['receipt'] = json.loads(receipt.read_text(encoding='utf-8'))
            if include_acknowledged or not item['acknowledged']:
                result.append(item)
        return result

    def ack(self, agent, message_id):
        message = self.message(message_id)
        if self.agent(agent) != message['to']:
            raise ValueError('Only the addressed recipient may acknowledge this message.')
        path = self.root / 'receipts' / (message_id + '.json')
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
        receipt = {'message_id': message_id, 'agent': agent, 'acknowledged_utc': now()}
        self.write('receipts', message_id, receipt)
        return receipt

    def presence(self, agent, state, task, files):
        self.agent(agent)
        if state not in STATES:
            raise ValueError('Invalid state.')
        data = {'agent': agent, 'state': state, 'task': task, 'files': files,
                'updated_utc': now(), 'note': 'Self-reported status; not a process heartbeat or an enforced file lock.'}
        self.write('presence', agent, data)
        return data

    def status(self):
        result = []
        for agent in AGENTS:
            path = self.root / 'presence' / (agent + '.json')
            item = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'agent': agent, 'state': 'unknown', 'updated_utc': None}
            item['unacknowledged_messages'] = len(self.inbox(agent))
            result.append(item)
        return result


def parser():
    command = argparse.ArgumentParser(description=__doc__)
    commands = command.add_subparsers(dest='command', required=True)
    send = commands.add_parser('send', help='Send an immutable message; prints its ID.')
    send.add_argument('--from', dest='sender', choices=AGENTS, required=True)
    send.add_argument('--to', dest='recipient', choices=AGENTS, required=True)
    send.add_argument('--subject', required=True)
    content = send.add_mutually_exclusive_group(required=True)
    content.add_argument('--message')
    content.add_argument('--file', help='UTF-8 file containing message body; preferred for multiline messages.')
    send.add_argument('--reply-to')
    inbox = commands.add_parser('inbox', help='Read unacknowledged messages without acknowledging them.')
    inbox.add_argument('--agent', choices=AGENTS, required=True)
    inbox.add_argument('--all', action='store_true')
    ack = commands.add_parser('ack', help='Explicit receipt by addressed agent.')
    ack.add_argument('--agent', choices=AGENTS, required=True)
    ack.add_argument('--id', required=True)
    show = commands.add_parser('show')
    show.add_argument('--id', required=True)
    commands.add_parser('status')
    presence = commands.add_parser('presence', help='Declare your own task and claimed files.')
    presence.add_argument('--agent', choices=AGENTS, required=True)
    presence.add_argument('--state', choices=STATES, required=True)
    presence.add_argument('--task', required=True)
    presence.add_argument('--files', nargs='*', default=[])
    watch = commands.add_parser('watch', help='Wait for pending messages, then exit; never executes content.')
    watch.add_argument('--agent', choices=AGENTS, required=True)
    watch.add_argument('--timeout', type=int, default=30)
    return command


def main(argv=None):
    args = parser().parse_args(argv)
    bridge = Bridge(Path(__file__).resolve().parent / 'mailbox')
    try:
        if args.command == 'send':
            body = Path(args.file).read_text(encoding='utf-8-sig') if args.file else args.message
            result = bridge.send(args.sender, args.recipient, args.subject, body, args.reply_to)
        elif args.command == 'inbox':
            result = bridge.inbox(args.agent, args.all)
        elif args.command == 'ack':
            result = bridge.ack(args.agent, args.id)
        elif args.command == 'show':
            result = bridge.message(args.id)
        elif args.command == 'presence':
            result = bridge.presence(args.agent, args.state, args.task, args.files)
        elif args.command == 'status':
            result = bridge.status()
        else:
            if not 1 <= args.timeout <= 60:
                raise ValueError('Watch timeout must be 1–60 seconds.')
            deadline = time.monotonic() + args.timeout
            while True:
                result = bridge.inbox(args.agent)
                if result or time.monotonic() >= deadline:
                    break
                time.sleep(min(1, max(0, deadline - time.monotonic())))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
