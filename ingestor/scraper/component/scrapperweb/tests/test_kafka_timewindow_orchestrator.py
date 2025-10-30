import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_timewindow_orchestrator import KafkaTimeWindowOrchestrator
from kafka_producer import KafkaProducerClient

class TestKafkaTimeWindowOrchestrator(unittest.TestCase):
    def setUp(self):
        self.mock_kafka_producer = Mock(spec=KafkaProducerClient)
        self.mock_kafka_producer.enabled = True
        self.mock_kafka_producer.send.return_value = True
        self.orchestrator = KafkaTimeWindowOrchestrator(
            window_size_minutes=1,
            kafka_producer=self.mock_kafka_producer
        )

    def test_should_refresh_initial(self):
        """Test that should_refresh returns True on initial run"""
        self.assertTrue(self.orchestrator.should_refresh())

    def test_should_refresh_before_window(self):
        """Test that should_refresh returns False before window time"""
        self.orchestrator.start_new_window()
        self.assertFalse(self.orchestrator.should_refresh())

    def test_should_refresh_after_window(self):
        """Test that should_refresh returns True after window time"""
        self.orchestrator.start_new_window()
        self.orchestrator.last_window_start = datetime.now() - timedelta(minutes=2)  # Set window to 2 minutes ago
        self.assertTrue(self.orchestrator.should_refresh())

    def test_article_processing(self):
        """Test that articles are processed correctly"""
        test_article = {
            'url': 'https://test.com/article1',
            'title': 'Test Article',
            'content': 'Test content'
        }

        # Process the article
        result = self.orchestrator.process_article(test_article)
        self.assertTrue(result)

        # Verify that kafka_producer.send was called with correct parameters
        self.mock_kafka_producer.send.assert_called_once_with(test_article)
        
        # Verify same article is not processed twice in same window
        self.mock_kafka_producer.send.reset_mock()
        result = self.orchestrator.process_article(test_article)
        self.assertFalse(result)
        self.mock_kafka_producer.send.assert_not_called()

    def test_window_reset(self):
        """Test that cache is cleared when starting new window"""
        test_article = {
            'url': 'https://test.com/article1',
            'title': 'Test Article',
            'content': 'Test content'
        }

        # Process article in first window
        self.orchestrator.process_article(test_article)
        
        # Start new window
        self.orchestrator.start_new_window()
        
        # Process same article in new window
        result = self.orchestrator.process_article(test_article)
        self.assertTrue(result)
        
        # Verify article was processed again
        self.assertEqual(self.mock_kafka_producer.send.call_count, 2)

if __name__ == '__main__':
    unittest.main()