#!/usr/bin/env python3
"""
Quick Start Example for DhanHQ Copy Trading System

This example demonstrates basic usage of the copy trading system.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import CopyTradingSystem
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def main():
    """Run the copy trading system."""
    print("="*60)
    print("DhanHQ Copy Trading System - Quick Start")
    print("="*60)
    print()
    
    # Create system instance
    system = CopyTradingSystem()
    
    try:
        # Start the system
        print("Starting copy trading system...")
        system.start()
        
        print()
        print("✅ System started successfully!")
        print("📊 Monitoring leader account for orders...")
        print("Press Ctrl+C to stop")
        print()
        
        # Keep running
        system.wait()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Shutting down...")
        system.stop()
        print("✅ System stopped gracefully")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        system.stop()
        raise

if __name__ == '__main__':
    main()

