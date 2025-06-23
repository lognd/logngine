#include <logngine/core/RSTTree.h>
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace logngine::core
{
    // ==========================================================
    //  R*-Tree (w/ traversal) implementation
    // ==========================================================

    // ----------------------------------------------------------
    //  R*-Tree Bounding Regions
    // ----------------------------------------------------------
#pragma region MBR

    template <size_t D>
    MinimumBoundingRegion<D>::MinimumBoundingRegion()
    {
        this->max.fill(-inf);
        this->min.fill(inf);
    }

    template <size_t D>
    double MinimumBoundingRegion<D>::area() const
    {
        double result = 1.0;
        for (size_t i = 0; i < D; ++i) result *= (this->max[i] - this->min[i]);
        return result;
    }

    template <size_t D>
    bool MinimumBoundingRegion<D>::contains(const std::array<double, D>& point) const
    {
        for (size_t i = 0; i < D; ++i)
            if (point[i] < this->min[i] || point[i] > this->max[i]) return false;
        return true;
    }

    template <size_t D>
    bool MinimumBoundingRegion<D>::overlaps(const MinimumBoundingRegion& other) const
    {
        // Separating axis theorem
        for (size_t i = 0; i < D; ++i)
            if (this->max[i] < other.min[i] || this->min[i] > other.max[i]) return false;
        return true;
    }

    template <size_t D>
    void MinimumBoundingRegion<D>::expand(const MinimumBoundingRegion& region)
    {
        for (size_t i = 0; i < D; ++i)
        {
            if (region.min[i] < this->min[i]) this->min[i] = region.min[i];
            if (region.max[i] > this->max[i]) this->max[i] = region.max[i];
        }
    }

    template <size_t D>
    void MinimumBoundingRegion<D>::expand(const std::array<double, D>& point)
    {
        for (size_t i = 0; i < D; ++i)
        {
            if (point[i] < this->min[i]) this->min[i] = point[i];
            if (point[i] > this->max[i]) this->max[i] = point[i];
        }
    }

#pragma endregion

#pragma region MBR Helper Functions

    template <size_t D>
    double point_to_box_distance_squared(const std::array<double, D>& point, const MBR<D>& box)
    {
        double dist_sq = 0.0;
        for (size_t i = 0; i < D; ++i)
        {
            if (point[i] < box.min[i]) dist_sq += (box.min[i] - point[i]) * (box.min[i] - point[i]);
            else if (point[i] > box.max[i]) dist_sq += (point[i] - box.max[i]) * (point[i] - box.max[i]);
        }
        return dist_sq;
    }

    void SplitTracker::update(const size_t axis, const size_t location, const double overlap, const double margin,
                              const double area)
    {
        this->axis = axis;
        this->location = location;
        this->overlap = overlap;
        this->margin = margin;
        this->area = area;
    }

    template <size_t D>
    double compute_overlap(MBR<D> A, MBR<D> B)
    {
        double volume = 1.0;
        for (size_t i = 0; i < D; ++i)
        {
            const double overlap = std::min(A.max[i], B.max[i]) - std::max(A.min[i], B.min[i]);
            if (overlap <= 0.0) return 0.0;
            volume *= overlap;
        }
        return volume;
    }

    template <size_t D>
    double compute_margin(MBR<D> A, MBR<D> B)
    {
        double sum = 0.0;
        for (size_t i = 0; i < D; ++i) sum += (A.max[i] - A.min[i]) + (B.max[i] - B.min[i]);
        return 2.0 * sum;
    }

    template <size_t D>
    double compute_area(MBR<D> A, MBR<D> B)
    {
        return A.area() + B.area();
    }

#pragma endregion

#pragma region Node

    namespace RSTNodeFN
    {
        template <size_t D, size_t N, size_t L, typename S>
        bool is_leaf(const RSTNode<D, N, L, S>& node)
        {
            return std::holds_alternative<RSTLeafNode<D, N, L, S>>(node);
        }

        template <size_t D, size_t N, size_t L, typename S>
        size_t get_size(const RSTNode<D, N, L, S>& node)
        {
            if (auto* internal = std::get_if<RSTInternalNode<D, N, L, S>>(&node)) return internal->size;
            if (auto* leaf = std::get_if<RSTLeafNode<D, N, L, S>>(&node)) return leaf->size;
            throw std::runtime_error("Did not receive an RSTNode in get_size...");
        }

        template <size_t D, size_t N, size_t L, typename S>
        bool is_full(const RSTNode<D, N, L, S>& node)
        {
            if (auto* internal = std::get_if<RSTInternalNode<D, N, L, S>>(&node)) return internal->is_full();
            if (auto* leaf = std::get_if<RSTLeafNode<D, N, L, S>>(&node)) return leaf->is_full();
            throw std::runtime_error("Did not receive an RSTNode in get_size...");
        }

        template <size_t D, size_t N, size_t L, typename S>
        std::optional<SplitResult<D, N, L, S>> insert(RSTNode<D, N, L, S>& node,
                                                      const std::array<double, D>& key, const S& value)
        {
            if (auto* internal = std::get_if<RSTInternalNode<D, N, L, S>>(&node))
                return internal->insert(key, value);
            if (auto* leaf = std::get_if<RSTLeafNode<D, N, L, S>>(&node))
                return leaf->insert(key, value);
            throw std::runtime_error("Did not receive an RSTNode in insert...");
        }
    }

#pragma endregion

    // ----------------------------------------------------------
    //  R*-Tree Leaf Nodes Helper Functions
    // ----------------------------------------------------------

#pragma region Insertion Helper Functions
    template <size_t D, size_t N, size_t L, typename S>
    std::array<SplitEntry<D, S>, N + 1> RSTLeafNode<D, N, L, S>::pack_entries(
        const std::array<std::optional<MBR<D>>, N>& subregions,
        const std::array<std::optional<S>, N>& children,
        const std::array<double, D>& key,
        const S& value)
    {
        std::array<SplitEntry<D, S>, N + 1> entries{};
        for (size_t i = 0; i < N; ++i)
        {
            if (!subregions[i] || !children[i])
                throw std::runtime_error("Corrupt node: missing subregion/child...");
            entries[i] = SplitEntry<D, S>{*subregions[i], *children[i]};
        }
        entries[N] = SplitEntry<D, S>{MBR<D>(key), value};
        return entries;
    }

    template <size_t D, size_t N, size_t L, typename S>
    SplitTracker RSTLeafNode<D, N, L, S>::find_best_split(std::array<SplitEntry<D, S>, N + 1>& entries)
    {
        SplitTracker best_split;
        for (size_t axis = 0; axis < D; ++axis)
        {
            std::sort(entries.begin(), entries.end(),
                      [axis](const SplitEntry<D, S>& a, const SplitEntry<D, S>& b)
                      {
                          return a.region.min[axis] < b.region.min[axis];
                      });

            for (size_t k = MIN_SPLIT_COUNT; k < L + 1 - MIN_SPLIT_COUNT; ++k)
            {
                MBR<D> lower{}, upper{};
                for (size_t j = 0; j < k; ++j) lower.expand(entries[j].region);
                for (size_t j = k; j < L + 1; ++j) upper.expand(entries[j].region);

                const double overlap = compute_overlap(lower, upper);
                if (overlap > best_split.overlap) continue;

                const double margin = compute_margin(lower, upper);
                const double area = compute_area(lower, upper);

                if (overlap < best_split.overlap)
                {
                    best_split.update(axis, k, overlap, margin, area);
                    continue;
                }
                if (margin < best_split.margin)
                {
                    best_split.update(axis, k, overlap, margin, area);
                    continue;
                }
                if (area < best_split.area)
                {
                    best_split.update(axis, k, overlap, margin, area);
                }
            }
        }

        if (best_split.overlap == inf)
            throw std::runtime_error("Could not find a valid split.");
        return best_split;
    }

    template <size_t D, size_t N, size_t L, typename S>
    void RSTLeafNode<D, N, L, S>::partition_entries(
        const std::array<SplitEntry<D, S>, L + 1>& sorted_entries,
        const size_t split_index,
        MBR<D>& lower,
        MBR<D>& upper,
        std::array<std::optional<MBR<D>>, L + 1>& lower_subregions,
        std::array<std::optional<S>, L + 1>& lower_children,
        std::array<std::optional<MBR<D>>, L + 1>& upper_subregions,
        std::array<std::optional<S>, L + 1>& upper_children)
    {
        for (size_t j = 0; j < split_index; ++j)
        {
            lower.expand(sorted_entries[j].region);
            lower_subregions[j] = sorted_entries[j].region;
            lower_children[j] = sorted_entries[j].value;
        }
        for (size_t j = split_index; j < L + 1; ++j)
        {
            upper.expand(sorted_entries[j].region);
            upper_subregions[j - split_index] = sorted_entries[j].region;
            upper_children[j - split_index] = sorted_entries[j].value;
        }
    }
#pragma endregion

    // ----------------------------------------------------------
    //  R*-Tree Leaf Nodes Member Functions
    // ----------------------------------------------------------
#pragma region Leaf Node Member Functions
    template <size_t D, size_t N, size_t L, typename S>
    std::optional<SplitResult<D, N, L, S>> RSTLeafNode<D, N, L, S>::insert(
        const std::array<double, D>& key, const S& value)
    {
        if (!is_full())
        {
            subregions[size] = key;
            children[size] = value;
            region.expand(key);
            ++size;
            return std::nullopt;
        }

        auto entries = pack_entries(subregions, children, key, value);
        SplitTracker best_split = find_best_split(entries);

        std::sort(entries.begin(), entries.end(),
                  [&best_split](const SplitEntry<D, S>& a, const SplitEntry<D, S>& b)
                  {
                      return a.region.min[best_split.axis] < b.region.min[best_split.axis];
                  });

        MBR<D> lower, upper;
        std::array<std::optional<MBR<D>>, L + 1> lower_subregions{}, upper_subregions{};
        std::array<std::optional<S>, L + 1> lower_children{}, upper_children{};

        partition_entries(entries, best_split.location,
                          lower, upper,
                          lower_subregions, lower_children,
                          upper_subregions, upper_children);

        this->region = std::move(lower);
        this->size = best_split.location;
        this->subregions = std::move(lower_subregions);
        this->children = std::move(lower_children);

        auto sibling = std::make_unique<RSTLeafNode<D, N, L, S>>(
            L + 1 - best_split.location,
            upper,
            std::move(upper_subregions),
            std::move(upper_children));

        return {SplitResult<D, N, L, S>{upper, std::move(sibling)}};
    }

    template <size_t D, size_t N, size_t L, typename S>
    void RSTLeafNode<D, N, L, S>::query(const std::array<double, D>& key,
                                        size_t k,
                                        MaxHeap<S>& result,
                                        const std::function<bool(const S&)>& filter) const
    {
        for (size_t i = 0; i < size; ++i)
        {
            if (!children[i]) continue;
            if (!filter(*children[i])) continue;

            double dist_sq = 0.0;
            for (size_t j = 0; j < D; ++j)
            {
                double diff = key[j] - subregions[i]->min[j]; // treat region as a point
                dist_sq += diff * diff;
            }

            if (result.size() < k)
            {
                result.emplace(dist_sq, *children[i]);
            }
            else if (dist_sq < result.top().first)
            {
                result.pop();
                result.emplace(dist_sq, *children[i]);
            }
        }
    }
#pragma endregion

    // ----------------------------------------------------------
    //  R*-Tree Internal Nodes Helper Functions
    // ----------------------------------------------------------

#pragma region Insertion Helper Functions
    template <size_t D, size_t N, size_t L, typename S>
    std::array<SplitEntry<D, std::shared_ptr<RSTNode<D, N, L, S>>>, N + 1>
    RSTInternalNode<D, N, L, S>::pack_entries(
        const std::array<std::optional<MBR<D>>, N>& subregions,
        const std::array<std::shared_ptr<RSTNode<D, N, L, S>>, N>& children,
        const MBR<D>& new_mbr,
        std::shared_ptr<RSTNode<D, N, L, S>> new_child)
    {
        std::array<SplitEntry<D, std::shared_ptr<RSTNode<D, N, L, S>>>, N + 1> entries{};
        for (size_t i = 0; i < N; ++i)
            entries[i] = {*subregions[i], children[i]};
        entries[N] = {new_mbr, std::move(new_child)};
        return entries;
    }

    template <size_t D, size_t N, size_t L, typename S>
    void RSTInternalNode<D, N, L, S>::partition_entries(
        const std::array<SplitEntry<D, std::shared_ptr<RSTNode<D, N, L, S>>>, L + 1>& sorted_entries,
        const size_t split_index,
        MBR<D>& lower, MBR<D>& upper,
        std::array<std::optional<MBR<D>>, L + 1>& lower_subregions,
        std::array<std::shared_ptr<RSTNode<D, N, L, S>>, L + 1>& lower_children,
        std::array<std::optional<MBR<D>>, L + 1>& upper_subregions,
        std::array<std::shared_ptr<RSTNode<D, N, L, S>>, L + 1>& upper_children)
    {
        for (size_t j = 0; j < split_index; ++j)
        {
            lower.expand(sorted_entries[j].region);
            lower_subregions[j] = sorted_entries[j].region;
            lower_children[j] = sorted_entries[j].value;
        }
        for (size_t j = split_index; j < L + 1; ++j)
        {
            upper.expand(sorted_entries[j].region);
            upper_subregions[j - split_index] = sorted_entries[j].region;
            upper_children[j - split_index] = sorted_entries[j].value;
        }
    }

    template <size_t D, size_t N, size_t L, typename S>
    size_t RSTInternalNode<D, N, L, S>::find_best_child_insertion(const MBR<D>& key_mbr)
    {
        size_t best_index = 0;
        double best_enlargement = inf;
        double best_area = inf;

        for (size_t i = 0; i < size; ++i)
        {
            if (!subregions[i]) continue;
            MBR<D> current = *subregions[i];
            double original_area = current.area();
            current.expand(key_mbr);
            const double enlargement = current.area() - original_area;

            if (enlargement < best_enlargement ||
                (enlargement == best_enlargement && original_area < best_area))
            {
                best_index = i;
                best_enlargement = enlargement;
                best_area = original_area;
            }
        }

        return best_index;
    }
#pragma endregion
    // ----------------------------------------------------------
    //  R*-Tree Internal Nodes
    // ----------------------------------------------------------
#pragma region Internal Node Member Functions
    template <size_t D, size_t N, size_t L, typename S>
    std::optional<SplitResult<D, N, L, S>> RSTInternalNode<D, N, L, S>::insert(
        const std::array<double, D>& key, const S& value)
    {
        MBR<D> key_mbr(key);
        size_t best_index = find_best_child_insertion(key_mbr);

        auto split = RSTNodeFN::insert(*children[best_index], key, value);
        if (!split)
        {
            subregions[best_index]->expand(key);
            region.expand(key);
            return std::nullopt;
        }

        if (!is_full())
        {
            subregions[size] = split->new_region;
            children[size] = std::move(split->sibling);
            region.expand(split->new_region);
            ++size;
            return std::nullopt;
        }

        // Prepare entries for splitting
        auto entries = pack_entries(subregions, children, split->new_region, std::move(split->sibling));
        auto best_split = RSTLeafNode<D, N, L, std::shared_ptr<RSTNode<D, N, L, S>>>::find_best_split(entries);

        std::sort(entries.begin(), entries.end(),
                  [&best_split](const auto& a, const auto& b)
                  {
                      return a.region.min[best_split.axis] < b.region.min[best_split.axis];
                  });

        // Partition entries
        MBR<D> lower, upper;
        std::array<std::optional<MBR<D>>, L + 1> lower_subregions{}, upper_subregions{};
        std::array<std::shared_ptr<RSTNode<D, N, L, S>>, L + 1> lower_children{}, upper_children{};

        partition_entries(entries, best_split.location,
                          lower, upper,
                          lower_subregions, lower_children,
                          upper_subregions, upper_children);

        // Finalize current node
        region = lower;
        size = best_split.location;
        subregions = std::move(lower_subregions);
        children = std::move(lower_children);

        // Create sibling node
        auto sibling = std::make_unique<RSTInternalNode<D, N, L, S>>();
        sibling->region = upper;
        sibling->size = L + 1 - best_split.location;
        sibling->subregions = std::move(upper_subregions);
        sibling->children = std::move(upper_children);

        return {SplitResult<D, N, L, S>{sibling->region, std::move(sibling)}};
    }

    template <size_t D, size_t N, size_t L, typename S>
    void RSTInternalNode<D, N, L, S>::query(const std::array<double, D>& key,
                                            size_t k,
                                            MaxHeap<S>& result,
                                            const std::function<bool(const S&)>& filter) const
    {
        using QueueEntry = std::pair<double, size_t>;
        std::priority_queue<QueueEntry, std::vector<QueueEntry>, std::greater<>> pq;

        for (size_t i = 0; i < size; ++i)
        {
            if (!subregions[i]) continue;
            double dist_sq = point_to_box_distance_squared(key, *subregions[i]);
            pq.emplace(dist_sq, i);
        }

        while (!pq.empty())
        {
            auto [_, i] = pq.top();
            pq.pop();
            if (children[i])
            {
                std::visit([&](const auto& child)
                {
                    child.query(key, k, result, filter);
                }, *children[i]);
            }
        }
    }
#pragma endregion
    // ----------------------------------------------------------
    //  R*-Tree Implementation
    // ----------------------------------------------------------
#pragma region RSTTree Implementation

    template <typename STORED_DATA_TYPE, size_t D_REGION, size_t N_CHILD, size_t N_KEYS>
    void RSTTree<STORED_DATA_TYPE, D_REGION, N_CHILD, N_KEYS>::insert(
        const std::array<double, D_REGION>& key,
        const STORED_DATA_TYPE& value)
    {
        using NodeT = RSTNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>;

        // Case 1: Tree is empty — create root node as leaf
        if (!root)
        {
            auto leaf = std::make_unique<RSTLeafNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>>();
            leaf->subregions[0] = MBR<D_REGION>(key);
            leaf->children[0] = value;
            leaf->region.expand(key);
            leaf->size = 1;
            root = std::make_unique<NodeT>(std::move(*leaf));
            return;
        }

        // Case 2: Delegate to node-specific insert logic
        auto split = RSTNodeFN::insert(*root, key, value);

        // Case 3: No split, just a successful insert
        if (!split) return;

        // Case 4: Root split occurred → make new root internal node
        auto new_root = std::make_unique<RSTInternalNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>>();

        new_root->children[0] = std::make_unique<NodeT>(std::move(*root));
        new_root->children[1] = std::move(split->sibling);
        new_root->subregions[0] = RSTNodeFN::is_leaf(*new_root->children[0])
                                      ? std::get<RSTLeafNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>>(
                                          *new_root->children[0]).region
                                      : std::get<RSTInternalNode<D_REGION, N_CHILD, N_KEYS, STORED_DATA_TYPE>>(
                                          *new_root->children[0]).region;
        new_root->subregions[1] = split->new_region;
        new_root->region = *new_root->subregions[0];
        new_root->region.expand(*new_root->subregions[1]);
        new_root->size = 2;

        root = std::make_unique<NodeT>(std::move(*new_root));
    }

    template <typename S, size_t D, size_t N, size_t L>
    std::vector<S> RSTTree<S, D, N, L>::query(const std::array<double, D>& key, size_t k) const
    {
        return query_with_filter(key, k, [](const S&) { return true; });
    }

    template <typename S, size_t D, size_t N, size_t L>
    std::vector<S> RSTTree<S, D, N, L>::query_with_filter(const std::array<double, D>& key,
                                                          size_t max,
                                                          const std::function<bool(const S&)>& filter) const
    {
        MaxHeap<S> result;

        if (!root) return {};

        std::visit([&](const auto& node) {
            node.query(key, max, result, filter);
        }, *root);

        std::vector<S> output;
        output.reserve(result.size());
        while (!result.empty())
        {
            output.push_back(result.top().second);
            result.pop();
        }

        std::reverse(output.begin(), output.end());
        return output;
    }

#pragma endregion
}
