#!/usr/bin/env python3
"""
Test ClaudeStreamer Class
"""

from claude_streamer import ClaudeStreamer

def test_class():
    """Test the ClaudeStreamer class"""
    print("Testing ClaudeStreamer class...")

    # Create streamer instance
    streamer = ClaudeStreamer()

    # Test streaming
    print("\n1. Testing stream method:")
    exit_code = streamer.stream("What is 2+2? Give a short answer.")

    print(f"\nExit code: {exit_code}")

    # Test get_response method
    print("\n2. Testing get_response method:")
    response, code = streamer.get_response("What is Python? One sentence only.")
    print(f"Response: {response}")
    print(f"Exit code: {code}")

if __name__ == "__main__":
    test_class()