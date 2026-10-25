import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { getSeries } from '../../api/client.ts'

/** Loads the horizon series. The API chooses which forecast to return. */
export function useSeries(
  startDay: string,
  endDay: string,
  horizonHours: number,
) {
  return useQuery({
    queryKey: ['series', startDay, endDay, horizonHours],
    queryFn: ({ signal }) =>
      getSeries(
        {
          start_day: startDay,
          end_day: endDay,
          horizon_hours: horizonHours,
        },
        signal,
      ),
    enabled: startDay <= endDay,
    placeholderData: keepPreviousData,
  })
}
