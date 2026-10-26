import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { getDecision } from '../../api/client.ts'

/** Loads the decision forecast. The API chooses the publish at or before the cutoff. */
export function useDecision(deliveryDay: string, cutoff: string) {
  return useQuery({
    queryKey: ['decision', deliveryDay, cutoff],
    queryFn: ({ signal }) =>
      getDecision({ delivery_day: deliveryDay, cutoff }, signal),
    enabled: deliveryDay.length > 0,
    placeholderData: keepPreviousData,
  })
}
