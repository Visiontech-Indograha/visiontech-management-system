"""Tests use a temporary mailbox. No receipt or reply is fabricated in the live bridge."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from bridge import Bridge


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='visiontech-bridge-test-')
        self.addCleanup(self.temp.cleanup)
        self.bridge = Bridge(self.temp.name)

    def test_round_trip_and_explicit_ack(self):
        sent = self.bridge.send('codex', 'gemini', 'Koordinasi', 'Uji pesan UTF-8 → peran dan SK.')
        self.assertEqual(self.bridge.inbox('codex'), [])
        self.assertEqual(len(self.bridge.inbox('gemini')), 1)
        self.assertEqual(len(self.bridge.inbox('gemini')), 1)  # reading is not acknowledgement
        with self.assertRaises(ValueError):
            self.bridge.ack('codex', sent['id'])
        receipt = self.bridge.ack('gemini', sent['id'])
        self.assertEqual(self.bridge.ack('gemini', sent['id']), receipt)
        self.assertEqual(self.bridge.inbox('gemini'), [])
        self.assertEqual(len(self.bridge.inbox('gemini', True)), 1)
        reply = self.bridge.send('gemini', 'codex', 'Balasan', 'Diterima.', sent['id'])
        self.assertEqual(self.bridge.inbox('codex')[0]['reply_to'], sent['id'])
        self.assertNotEqual(reply['id'], sent['id'])

    def test_ids_and_sender_validation(self):
        for value in ('../../index.html', '', '/tmp/message'):
            with self.assertRaises(ValueError):
                self.bridge.message(value)
        with self.assertRaises(ValueError):
            self.bridge.send('codex', 'codex', 'x', 'y')
        with self.assertRaises(ValueError):
            self.bridge.send('other', 'gemini', 'x', 'y')
        with self.assertRaises(ValueError):
            self.bridge.send('codex', 'gemini', '', 'y')

    def test_concurrent_messages_do_not_overwrite(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            messages = list(pool.map(lambda n: self.bridge.send('codex', 'gemini', str(n), 'test'), range(40)))
        self.assertEqual(len({m['id'] for m in messages}), 40)
        self.assertEqual(len(self.bridge.inbox('gemini')), 40)
        self.assertEqual(list(Path(self.temp.name).rglob('*.tmp')), [])

    def test_presence_is_self_reported_not_implied_delivery(self):
        initial = self.bridge.status()
        self.assertTrue(all(item['state'] == 'unknown' for item in initial))
        self.bridge.presence('codex', 'waiting', 'Review', ['coordination/codex.md'])
        current = self.bridge.status()
        self.assertEqual(current[0]['state'], 'waiting')
        self.assertEqual(current[1]['state'], 'unknown')


if __name__ == '__main__':
    unittest.main()
