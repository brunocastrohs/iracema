// src/features/Chat/fca/fcaDraftFactory.js

export const DEFAULT_LIMIT = 100;

export function makeInitialFcaDraft(overrides = {}) {
  return {
    select: [],
    where: [],
    group_by: [],
    order_by: [],
    limit: DEFAULT_LIMIT,
    offset: 0,
    // flag interna do front: quando true, o payload manda select=[] e o backend interpreta como SELECT *
    _selectAll: false,
    ...overrides,
  };
}
