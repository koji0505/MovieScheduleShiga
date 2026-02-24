import { useState, useEffect, useMemo } from 'react';
import { DATA_URL } from '../constants';
import { buildMovieIndex, buildMovieList, getAvailableDates } from '../utils/schedule';

export function useSchedule() {
  const [rawData, setRawData]     = useState(null);
  const [loading, setLoading]     = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]         = useState(null);
  const [updatedAt, setUpdatedAt] = useState('');

  const loadData = async () => {
    try {
      const resp = await fetch(DATA_URL);
      const data = await resp.json();
      setRawData(data);
      if (data.updated_at) {
        setUpdatedAt(new Date(data.updated_at).toLocaleString('ja-JP'));
      }
      setError(null);
    } catch {
      setError('データの読み込みに失敗しました');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const movieIndex = useMemo(
    () => rawData ? buildMovieIndex(rawData) : null,
    [rawData]
  );

  const movieList = useMemo(
    () => rawData ? buildMovieList(rawData) : [],
    [rawData]
  );

  const theaterNames = useMemo(
    () => rawData ? Object.keys(rawData.theaters) : [],
    [rawData]
  );

  const availableDates = useMemo(
    () => rawData ? getAvailableDates(rawData) : [],
    [rawData]
  );

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  return { rawData, movieList, movieIndex, theaterNames, availableDates, loading, refreshing, error, updatedAt, onRefresh, loadData };
}
