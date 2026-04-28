import { useEffect, useState } from 'react'
import { apiRequest } from '../config/api'

export function useApiResource(path, fallbackValue) {
  const [data, setData] = useState(fallbackValue)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isMounted = true

    apiRequest(path)
      .then((payload) => {
        if (isMounted) setData(payload)
      })
      .catch((requestError) => {
        if (isMounted) setError(requestError.message)
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [path])

  return { data, loading, error, setData }
}
