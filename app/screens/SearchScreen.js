import React, { useState, useMemo, useEffect } from 'react';
import {
  StyleSheet, View, Text, TextInput,
  FlatList, TouchableOpacity, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { COLORS } from '../constants';
import { useScheduleContext } from '../context/ScheduleContext';
import { filterMovies } from '../utils/schedule';
import { DateFilter } from '../components/DateFilter';
import { TheaterFilter } from '../components/TheaterFilter';
import { MovieCard } from '../components/MovieCard';

export function SearchScreen({ navigation, route }) {
  const { movieIndex, theaterNames, availableDates, refreshing, updatedAt, onRefresh } =
    useScheduleContext();
  const [query, setQuery]                   = useState('');
  const [selectedDate, setSelectedDate]     = useState('');
  const [selectedTheater, setSelectedTheater] = useState('');

  // HomeScreen からタイトルで遷移してきた場合に初期値設定
  useEffect(() => {
    if (route.params?.title) {
      setQuery(route.params.title);
    }
  }, [route.params?.title]);

  const filteredMovies = useMemo(
    () => movieIndex ? filterMovies(movieIndex, query, selectedDate, selectedTheater) : [],
    [movieIndex, query, selectedDate, selectedTheater]
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" backgroundColor={COLORS.primary} />

      <View style={styles.header}>
        <Text style={styles.headerTitle}>スケジュール検索</Text>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backBtnText}>🏠 ホーム</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.controls}>
        <TextInput
          style={styles.searchInput}
          placeholder="映画タイトルで検索..."
          value={query}
          onChangeText={setQuery}
          clearButtonMode="while-editing"
        />
        <TheaterFilter
          theaters={theaterNames}
          selectedTheater={selectedTheater}
          onSelectTheater={setSelectedTheater}
        />
        <DateFilter
          dates={availableDates}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />
        {updatedAt ? <Text style={styles.updatedAt}>更新: {updatedAt}</Text> : null}
      </View>

      <FlatList
        data={filteredMovies}
        keyExtractor={item => item.title}
        renderItem={({ item }) => <MovieCard movie={item} />}
        ListEmptyComponent={<Text style={styles.noResults}>該当する映画が見つかりません</Text>}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[COLORS.primary]} />}
        contentContainerStyle={styles.listContent}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: COLORS.background },
  header: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  backBtn: {
    backgroundColor: COLORS.accent,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  backBtnText: { color: COLORS.white, fontSize: 13, fontWeight: '600' },
  headerTitle: { color: COLORS.white, fontSize: 18, fontWeight: '700', letterSpacing: 0.5, flex: 1 },
  controls: {
    backgroundColor: COLORS.white,
    paddingHorizontal: 12, paddingTop: 10, paddingBottom: 4,
    borderBottomWidth: 1, borderBottomColor: '#eee',
  },
  searchInput: {
    borderWidth: 2, borderColor: COLORS.border, borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 10,
    fontSize: 16, marginBottom: 8,
  },
  updatedAt:   { fontSize: 11, color: COLORS.textMuted, textAlign: 'right', paddingBottom: 6 },
  listContent: { padding: 12 },
  noResults:   { textAlign: 'center', color: COLORS.textMuted, padding: 48, fontSize: 15 },
});
