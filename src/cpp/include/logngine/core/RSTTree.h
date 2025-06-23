#pragma once

#include <vector>
#include <array>
#include <chrono>
#include <optional>
#include <variant>
#include <memory>
#include <queue>
#include <limits>
#include <functional>
#include <stdexcept>
#include <algorithm>

namespace logngine::core
{
    // ==========================================================
    //  Compile-Time Utilities and Constants
    // ==========================================================
#pragma region Compile-Time Utilities and Constants

    consteval size_t ceval_min(const size_t a, const size_t b) { return a < b ? a : b; }
    consteval size_t ceval_max(const size_t a, const size_t b) { return a > b ? a : b; }
    constexpr double inf = std::numeric_limits<double>::infinity();
    constexpr double nan = std::numeric_limits<double>::quiet_NaN();

#pragma endregion

    // ==========================================================
    //  R*-Tree Bounding Regions
    // ==========================================================
#pragma region Minimum Bounding Regions

    template <size_t D>
    struct MinimumBoundingRegion
    {
        MinimumBoundingRegion();

        explicit MinimumBoundingRegion(const std::array<double, D>& point) : min(point), max(point)
        {
        }

        std::array<double, D> min;
        std::array<double, D> max;

        bool contains(const std::array<double, D>& point) const;
        bool overlaps(const MinimumBoundingRegion& other) const;
        void expand(const std::array<double, D>& point);
        void expand(const MinimumBoundingRegion& region);
        [[nodiscard]] double area() const;
    };

    template <size_t D>
    using MBR = MinimumBoundingRegion<D>;

    template <typename T>
    using MaxHeap = std::priority_queue<std::pair<double, T>>;

#pragma endregion


    // ==========================================================
    //  R*-Tree Forward Declarations
    // ==========================================================
#pragma region Forward Declarations

    template <size_t D, size_t N, size_t L, typename S>
    struct RSTInternalNode;
    template <size_t D, size_t N, size_t L, typename S>
    struct RSTLeafNode;
    template <size_t D, size_t N, size_t L, typename S>
    using RSTNode = std::variant<RSTInternalNode<D, N, L, S>, RSTLeafNode<D, N, L, S>>;

    template <typename STORED_DATA_TYPE, size_t D_REGION, size_t N_CHILD, size_t N_KEYS = N_CHILD>
    class RSTTree;

#pragma endregion

    // ==========================================================
    //  R*-Tree Node Utilities
    // ==========================================================
#pragma region Node Utilities

    template <size_t D, typename S>
    struct SplitEntry
    {
        MBR<D> region;
        S value;
    };

    struct SplitTracker
    {
        size_t axis = 0;
        size_t location = 0;
        double overlap = inf;
        double margin = inf;
        double area = inf;

        void update(size_t axis, size_t location, double overlap, double margin, double area);
    };

    struct InsertionAreaTracker
    {
        size_t location = 0;
        double best_enlargement = inf;
        double best_area = inf;
    };

    template <size_t D, size_t N, size_t L, typename S>
    struct SplitResult
    {
        MBR<D> new_region;
        std::unique_ptr<RSTNode<D, N, L, S>> sibling;
    };

#pragma endregion

    // ==========================================================
    //  R*-Tree Node Function Utilities
    // ==========================================================
#pragma region Node Variant Function Utilities

    namespace RSTNodeFN
    {
        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] bool is_leaf(const RSTNode<D, N, L, S>& node);

        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] size_t get_size(const RSTNode<D, N, L, S>& node);

        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] bool is_full(const RSTNode<D, N, L, S>& node);

        template <size_t D, size_t N, size_t L, typename S>
        [[nodiscard]] std::optional<SplitResult<D, N, L, S>>
        insert(RSTNode<D, N, L, S>& node, const std::array<double, D>& key, const S& value);
    }

#pragma endregion

    // ==========================================================
    //  R*-Tree Leaf Node
    // ==========================================================
#pragma region Leaf Node

    template <size_t D, size_t N, size_t L, typename S>
    struct RSTLeafNode
    {
        static constexpr size_t MIN_SPLIT_COUNT = ceval_max(static_cast<size_t>(RSTTree<S, D, N, L>::MIN_SPLIT * N),
                                                            static_cast<size_t>(1));

        size_t size = 0;
        MBR<D> region{};
        std::array<std::optional<MBR<D>>, L> subregions{};
        std::array<std::optional<S>, L> children{};

        RSTLeafNode(const size_t size,
                    const MBR<D>& region,
                    std::array<std::optional<MBR<D>>, L + 1> subregions,
                    std::array<std::optional<S>, L + 1> children)
            : size(size), region(region), subregions(std::move(subregions)), children(std::move(children))
        {
        }

        // Querying
        void query(const std::array<double, D>& key, size_t k, MaxHeap<S>& result, const std::function<bool(const S&)>& filter, const std::array<double, D>& scale) const;
        std::optional<SplitResult<D, N, L, S>> insert(const std::array<double, D>& key, const S& value);
        [[nodiscard]] bool is_full() const { return this->size == L; }

    private:

        // Helper functions
        static std::array<SplitEntry<D, S>, N + 1> pack_entries(
            const std::array<std::optional<MBR<D>>, N>& subregions,
            const std::array<std::optional<S>, N>& children,
            const std::array<double, D>& key,
            const S& value);

        static SplitTracker find_best_split(std::array<SplitEntry<D, S>, N + 1>& entries);

        static void partition_entries(
            const std::array<SplitEntry<D, S>, L + 1>& sorted_entries,
            size_t split_index,
            MBR<D>& lower,
            MBR<D>& upper,
            std::array<std::optional<MBR<D>>, L + 1>& lower_subregions,
            std::array<std::optional<S>, L + 1>& lower_children,
            std::array<std::optional<MBR<D>>, L + 1>& upper_subregions,
            std::array<std::optional<S>, L + 1>& upper_children);
    };

#pragma endregion

    // ==========================================================
    //  R*-Tree Internal Node
    // ==========================================================
#pragma region Internal Node

    template <size_t D, size_t N, size_t L, typename S>
    struct RSTInternalNode
    {
        static constexpr size_t MIN_SPLIT_COUNT = ceval_max(static_cast<size_t>(RSTTree<S, D, N, L>::MIN_SPLIT * N),
                                                            static_cast<size_t>(1));

        size_t size = 0;
        MBR<D> region{};
        std::array<std::optional<MBR<D>>, N> subregions{};
        std::array<std::unique_ptr<RSTNode<D, N, L, S>>, N> children{};

        // Querying
        void query(const std::array<double, D>& key, size_t k, MaxHeap<S>& result, const std::function<bool(const S&)>& filter, const std::array<double, D>& scale) const;
        std::optional<SplitResult<D, N, L, S>> insert(const std::array<double, D>& key, const S& value);
        [[nodiscard]] bool is_full() const { return this->size == N; }

    private:
        // Helper function
        static std::array<SplitEntry<D, std::shared_ptr<RSTNode<D, N, L, S>>>, N + 1>
        pack_entries(const std::array<std::optional<MBR<D>>, N>& subregions,
                     const std::array<std::shared_ptr<RSTNode<D, N, L, S>>, N>& children,
                     const MBR<D>& new_mbr,
                     std::shared_ptr<RSTNode<D, N, L, S>> new_child);

        void partition_entries(
            const std::array<SplitEntry<D, std::shared_ptr<RSTNode<D, N, L, S>>>, L + 1>& sorted_entries,
            size_t split_index,
            MBR<D>& lower, MBR<D>& upper,
            std::array<std::optional<MBR<D>>, L + 1>& lower_subregions,
            std::array<std::shared_ptr<RSTNode<D, N, L, S>>, L + 1>& lower_children,
            std::array<std::optional<MBR<D>>, L + 1>& upper_subregions,
            std::array<std::shared_ptr<RSTNode<D, N, L, S>>, L + 1>& upper_children);

        size_t find_best_child_insertion(const MBR<D>& key_mbr);
    };

#pragma endregion

    // ==========================================================
    //  R*-Tree Public Interface
    // ==========================================================
#pragma region RSTTree

    template <typename STORED_DATA_TYPE, size_t D_REGION, size_t N_CHILD, size_t N_KEYS>
    class RSTTree
    {
    public:
        static constexpr double MIN_SPLIT = 0.25;

        void insert(const std::array<double, D_REGION>& key, const STORED_DATA_TYPE& value);
        std::vector<STORED_DATA_TYPE> query(const std::array<double, D_REGION>& key, size_t max = 1, const std::array<double, D_REGION>& scale) const;
        std::vector<STORED_DATA_TYPE> query_with_filter(const std::array<double, D_REGION>& key, size_t max = 1, const std::function<bool(const STORED_DATA_TYPE&)>& filter, const std::array<double, D_REGION>& scale) const;

    private:
        std::unique_ptr<RSTNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>> root = nullptr;
    };

#pragma endregion
} // namespace logngine::core
