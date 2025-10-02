# Task-003: Implementation Patches - TODO

## Goal
Implement all identified gaps from Task-002 audit to make the copy trading system production-ready.

## First Principles Breakdown

### Problem
The initial codebase (Task-001) handled basic order placement but lacked critical functionality for:
- Order cancellations
- Order modifications
- Execution tracking
- Missed order recovery
- Missing order parameters (trigger price, validity, disclosed quantity)
- Rate limiting
- Market hours validation

### Solution Approach
1. **Patch WebSocket Manager**: Handle all order statuses (not just new orders)
2. **Enhance Order Manager**: Add cancel, modify, and execution handlers
3. **Fix Order Parameters**: Extract and pass all order parameters correctly
4. **Add Rate Limiting**: Implement token bucket for API calls
5. **Add Market Hours Check**: Validate trading hours before placing orders
6. **Missed Order Recovery**: Fetch and replay orders after reconnection

## Task Checklist

### Planning Phase
- [x] Review Task-002 audit findings
- [x] Prioritize critical, high, and medium issues
- [x] Plan implementation strategy
- [x] Create Task-003 folder structure

### Implementation Phase - CRITICAL Issues
- [x] Fix order cancellation handling
  - [x] Update WebSocket to handle CANCELLED status
  - [x] Add cancel_order() method to OrderManager
  - [x] Route cancellation events in main orchestrator
- [x] Fix order modification handling
  - [x] Update WebSocket to handle MODIFIED status
  - [x] Add modify_order() method to OrderManager
  - [x] Route modification events in main orchestrator
- [x] Fix missed orders during disconnect
  - [x] Add _fetch_missed_orders() to WebSocket manager
  - [x] Track disconnect/reconnect state
  - [x] Fetch orders since last_leader_event_ts on reconnection
  - [x] Pass leader_client to WebSocket manager

### Implementation Phase - HIGH Priority
- [x] Fix trigger price for SL orders
  - [x] Extract triggerPrice from leader order
  - [x] Pass to _place_follower_order()
  - [x] Include in API call for SL/SL-M orders
  - [x] Save to database
- [x] Fix validity hardcoding
  - [x] Extract validity from leader order (default: DAY)
  - [x] Pass to _place_follower_order()
  - [x] Include in API call
  - [x] Save to database
- [x] Fix execution tracking
  - [x] Add handle_execution() method
  - [x] Track filled quantity and price
  - [x] Log execution events
  - [x] Compare leader vs follower execution timing
- [x] Add rate limiting
  - [x] Implement token bucket algorithm
  - [x] Add _wait_for_rate_limit() method
  - [x] Apply to all API calls (place, modify, cancel)
  - [x] Make rate limit configurable (10 req/sec default)

### Implementation Phase - MEDIUM Priority
- [x] Fix disclosed quantity
  - [x] Extract disclosedQuantity from leader order
  - [x] Calculate proportional follower disclosed qty
  - [x] Pass to API call
  - [x] Save to database
- [x] Add market hours validation
  - [x] Implement _is_market_open() method
  - [x] Check timezone (IST)
  - [x] Validate against exchange hours
  - [x] Log warning if market closed
  - [x] Add pytz dependency

### Testing & Documentation
- [x] Update requirements.txt (add pytz)
- [x] Create comprehensive patch documentation
- [x] Document all changes with code examples
- [x] Update changelogs
- [ ] Create test scenarios for new functionality
- [ ] Update README with new capabilities

### Deployment
- [ ] Test patched code in sandbox environment
- [ ] Validate all scenarios from Task-002
- [ ] Measure latency improvements
- [ ] Deploy to production

## Constraints
- Must maintain backward compatibility with existing database
- Must not break existing order placement flow
- Must respect DhanHQ API rate limits
- Changes must be atomic and testable

## Expected Outcome
A production-ready copy trading system that:
1. ✅ Handles all order lifecycle events (place, modify, cancel, execute)
2. ✅ Recovers from disconnections without missing orders
3. ✅ Replicates all order parameters accurately
4. ✅ Respects API rate limits
5. ✅ Validates market hours
6. ✅ Tracks execution and slippage
7. 🔄 Has comprehensive error handling and logging
8. 🔄 Passes all test scenarios from Task-002

## Dependencies
- Task-002 audit findings (COMPREHENSIVE_SCENARIOS.md, CODE_GAPS_ANALYSIS.md)
- Existing Task-001 codebase
- DhanHQ v2 SDK documentation

## Related Files
- `/tasks/Task-002-Scenario-Analysis-Audit/analysis/CODE_GAPS_ANALYSIS.md` - Detailed fixes needed
- `/tasks/Task-002-Scenario-Analysis-Audit/analysis/COMPREHENSIVE_SCENARIOS.md` - Test scenarios
- All source files in `/tasks/Task-001-Copy-Trading-Architecture/src/`

## Status
**IN PROGRESS** - Core patches completed, testing and documentation in progress

## Notes
- All patches marked with ✅ ADDED or ✅ FIXED comments for traceability
- Rate limiting uses thread-safe deque for timestamp tracking
- Market hours validation uses pytz for accurate IST timing
- Missed order recovery queries DB for last_leader_event_ts
- All new methods have comprehensive error handling and logging

