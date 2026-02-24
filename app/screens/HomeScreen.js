import React from 'react';
import {
  StyleSheet, View, Text, Image, FlatList,
  TouchableOpacity, ActivityIndicator, RefreshControl, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { COLORS } from '../constants';
import { useScheduleContext } from '../context/ScheduleContext';

export function HomeScreen({ navigation }) {
  const { movieList, loading, refreshing, error, updatedAt, onRefresh, loadData } = useScheduleContext();

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={COLORS.primary} />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity onPress={loadData} style={styles.retryButton}>
          <Text style={styles.retryText}>再試行</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const renderItem = ({ item }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => navigation.navigate('Search', { title: item.title })}
      activeOpacity={0.75}
    >
      {item.poster_url ? (
        <Image source={{ uri: item.poster_url }} style={styles.poster} resizeMode="cover" />
      ) : (
        <View style={styles.posterPlaceholder}>
          <Text style={styles.placeholderText}>No Image</Text>
        </View>
      )}
      <Text style={styles.cardTitle} numberOfLines={2}>{item.title}</Text>
      <TouchableOpacity
        onPress={() => Linking.openURL(`https://moviewalker.jp/mv${item.movie_id}/`)}
        style={styles.detailBtn}
      >
        <Text style={styles.detailBtnText}>詳細</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="light" backgroundColor={COLORS.primary} />
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <Text style={styles.headerTitle}>滋賀映画スケジュール</Text>
          <TouchableOpacity
            onPress={() => navigation.navigate('Search', {})}
            style={styles.searchBtn}
          >
            <Text style={styles.searchBtnText}>🔍 検索</Text>
          </TouchableOpacity>
        </View>
        {updatedAt ? <Text style={styles.updatedAt}>更新: {updatedAt}</Text> : null}
      </View>
      <FlatList
        data={movieList}
        keyExtractor={item => item.title}
        renderItem={renderItem}
        numColumns={2}
        columnWrapperStyle={styles.row}
        ListEmptyComponent={<Text style={styles.noResults}>上映中の映画がありません</Text>}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[COLORS.primary]} />}
        contentContainerStyle={styles.listContent}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: COLORS.background },
  center:       { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header:       { backgroundColor: COLORS.primary, paddingHorizontal: 16, paddingVertical: 14 },
  headerRow:    { flexDirection: 'row', alignItems: 'center' },
  headerTitle:  { color: COLORS.white, fontSize: 18, fontWeight: '700', letterSpacing: 0.5, flex: 1 },
  searchBtn: {
    backgroundColor: COLORS.accent,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  searchBtnText: { color: COLORS.white, fontSize: 13, fontWeight: '600' },
  updatedAt:    { color: 'rgba(255,255,255,0.75)', fontSize: 11, marginTop: 4 },
  listContent:  { padding: 10 },
  row:          { gap: 10 },
  card: {
    flex: 1,
    backgroundColor: COLORS.white,
    borderRadius: 10,
    marginBottom: 10,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
  },
  poster: { width: '100%', aspectRatio: 2 / 3 },
  posterPlaceholder: {
    width: '100%',
    aspectRatio: 2 / 3,
    backgroundColor: '#ddd',
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: { color: '#999', fontSize: 12 },
  cardTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: COLORS.primary,
    padding: 8,
    paddingBottom: 4,
    lineHeight: 18,
  },
  detailBtn: { alignSelf: 'flex-start', marginHorizontal: 8, marginBottom: 8 },
  detailBtnText: { fontSize: 12, color: COLORS.textLight, textDecorationLine: 'underline' },
  noResults:    { textAlign: 'center', color: COLORS.textMuted, padding: 48, fontSize: 15 },
  errorText:    { color: COLORS.error, fontSize: 15, marginBottom: 16 },
  retryButton:  { backgroundColor: COLORS.primary, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8 },
  retryText:    { color: COLORS.white, fontSize: 15 },
});
