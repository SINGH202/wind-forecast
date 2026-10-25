import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { getMetrics } from '../../api/client.ts'

/** Loads accuracy for the selected days and cutoff. The API computes the metrics. */
export function useMetrics(startDay: string, endDay: string, cutoff: string) {
  return useQuery({
    queryKey: ['metrics', startDay, endDay, cutoff],
    queryFn: ({ signal }) =>
      getMetrics({ start_day: startDay, end_day: endDay, cutoff }, signal),
    enabled: startDay <= endDay,
    placeholderData: keepPreviousData,
  })
}
